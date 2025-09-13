import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import re

# MUST BE FIRST: Set page config
st.set_page_config(
    page_title="🏦 Bank Statement RAG",
    page_icon="🏦",
    layout="wide"
)

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

def main():
    st.title("🏦 Bank Statement RAG System")
    st.markdown("Upload your bank statements and search through your transactions")
    
    # Initialize session state
    if 'transactions_df' not in st.session_state:
        st.session_state.transactions_df = pd.DataFrame()
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {}
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🧭 Navigation")
        page = st.radio(
            "Choose a section:",
            ["📁 Upload & Process", "🔍 Search & Query", "📊 Analytics"],
            index=0
        )
        
        # Show data status
        if not st.session_state.transactions_df.empty:
            st.success(f"✅ {len(st.session_state.transactions_df)} transactions loaded")
            
            # Show detected columns
            if st.session_state.column_mapping:
                st.info("🔍 **Detected Columns:**")
                for key, value in st.session_state.column_mapping.items():
                    if value:
                        st.write(f"• {key}: `{value}`")
        else:
            st.warning("No data loaded")
    
    # Main content
    if page == "📁 Upload & Process":
        render_upload_page()
    elif page == "🔍 Search & Query":
        render_search_page()
    elif page == "📊 Analytics":
        render_analytics_page()

def detect_columns(df):
    """Smart column detection for bank statement formats"""
    columns = df.columns.str.lower().str.strip()
    
    # Date column patterns
    date_patterns = ['date', 'transaction date', 'posted date', 'trans date', 'posting date', 'effective date']
    date_col = None
    for pattern in date_patterns:
        matches = [col for col in df.columns if pattern in col.lower()]
        if matches:
            date_col = matches[0]
            break
    
    # Description column patterns  
    desc_patterns = ['description', 'desc', 'memo', 'transaction', 'details', 'payee', 'merchant', 'reference', 'transaction details']
    desc_col = None
    for pattern in desc_patterns:
        matches = [col for col in df.columns if pattern in col.lower()]
        if matches:
            desc_col = matches[0]
            break
    
    # Amount column patterns
    amount_patterns = ['amount', 'transaction amount', 'value', 'sum', 'total']
    amount_col = None
    for pattern in amount_patterns:
        matches = [col for col in df.columns if pattern in col.lower()]
        if matches:
            amount_col = matches[0]
            break
    
    # Check for separate debit/credit columns
    debit_col = None
    credit_col = None
    debit_patterns = ['debit', 'withdrawal', 'outgoing', 'expense']
    credit_patterns = ['credit', 'deposit', 'incoming', 'income']
    
    for pattern in debit_patterns:
        matches = [col for col in df.columns if pattern in col.lower()]
        if matches:
            debit_col = matches[0]
            break
    
    for pattern in credit_patterns:
        matches = [col for col in df.columns if pattern in col.lower()]
        if matches:
            credit_col = matches[0]
            break
    
    return {
        'date': date_col,
        'description': desc_col,
        'amount': amount_col,
        'debit': debit_col,
        'credit': credit_col
    }

def process_dataframe(df, column_mapping):
    """Process and standardize the dataframe"""
    processed_df = df.copy()
    
    # Handle date column
    if column_mapping['date']:
        processed_df['date'] = pd.to_datetime(processed_df[column_mapping['date']], errors='coerce')
    
    # Handle description column
    if column_mapping['description']:
        processed_df['description'] = processed_df[column_mapping['description']].astype(str).str.strip()
    
    # Handle amount columns
    if column_mapping['amount']:
        # Single amount column
        processed_df['amount'] = pd.to_numeric(
            processed_df[column_mapping['amount']].astype(str).str.replace(r'[$,()]', '', regex=True), 
            errors='coerce'
        )
    elif column_mapping['debit'] and column_mapping['credit']:
        # Separate debit/credit columns
        debit = pd.to_numeric(
            processed_df[column_mapping['debit']].astype(str).str.replace(r'[$,()]', '', regex=True).fillna('0'), 
            errors='coerce'
        ).fillna(0)
        credit = pd.to_numeric(
            processed_df[column_mapping['credit']].astype(str).str.replace(r'[$,()]', '', regex=True).fillna('0'), 
            errors='coerce'
        ).fillna(0)
        processed_df['amount'] = credit - debit  # Credits positive, debits negative
    
    # Add transaction type
    if 'amount' in processed_df.columns:
        processed_df['transaction_type'] = processed_df['amount'].apply(
            lambda x: 'Income' if x > 0 else 'Expense' if x < 0 else 'Zero'
        )
    
    # Remove rows with missing critical data
    if 'date' in processed_df.columns and 'amount' in processed_df.columns:
        processed_df = processed_df.dropna(subset=['date', 'amount'])
    
    return processed_df

def render_upload_page():
    st.header("📁 Upload & Process Bank Statements")
    
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx', 'xls'])
    
    if uploaded_file is not None:
        try:
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File uploaded! {len(df)} rows, {len(df.columns)} columns found.")
            
            # Show original columns
            st.subheader("📋 Original File Columns")
            col_info = []
            for i, col in enumerate(df.columns):
                col_info.append(f"{i+1}. `{col}` ({df[col].dtype})")
            st.write("\n".join(col_info))
            
            # Auto-detect columns
            column_mapping = detect_columns(df)
            st.session_state.column_mapping = column_mapping
            
            st.subheader("🔍 Auto-Detected Column Mapping")
            
            # Show detection results
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Detected Mappings:**")
                for key, value in column_mapping.items():
                    if value:
                        st.success(f"✅ {key.title()}: `{value}`")
                    else:
                        st.error(f"❌ {key.title()}: Not found")
            
            with col2:
                st.write("**Manual Override (if needed):**")
                # Allow manual column selection
                date_col = st.selectbox("Date Column:", [""] + list(df.columns), 
                                      index=list(df.columns).index(column_mapping['date'])+1 if column_mapping['date'] else 0)
                desc_col = st.selectbox("Description Column:", [""] + list(df.columns),
                                      index=list(df.columns).index(column_mapping['description'])+1 if column_mapping['description'] else 0)
                amount_col = st.selectbox("Amount Column:", [""] + list(df.columns),
                                        index=list(df.columns).index(column_mapping['amount'])+1 if column_mapping['amount'] else 0)
                
                # Update mapping if manual selection made
                if date_col: column_mapping['date'] = date_col
                if desc_col: column_mapping['description'] = desc_col  
                if amount_col: column_mapping['amount'] = amount_col
            
            # Process the data if we have minimum required columns
            if column_mapping['description'] and (column_mapping['amount'] or (column_mapping['debit'] and column_mapping['credit'])):
                
                if st.button("🔄 Process Data", type="primary"):
                    with st.spinner("Processing data..."):
                        processed_df = process_dataframe(df, column_mapping)
                        st.session_state.transactions_df = processed_df
                        st.session_state.column_mapping = column_mapping
                        
                        st.success("✅ Data processed successfully!")
                        
                        # Show processed preview
                        st.subheader("📊 Processed Data Preview")
                        display_cols = ['date', 'description', 'amount', 'transaction_type']
                        available_cols = [col for col in display_cols if col in processed_df.columns]
                        st.dataframe(processed_df[available_cols].head(10))
                        
                        # Show stats
                        if 'amount' in processed_df.columns:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Transactions", len(processed_df))
                            with col2:
                                total = processed_df['amount'].sum()
                                st.metric("Net Amount", f"${total:,.2f}")
                            with col3:
                                avg = processed_df['amount'].mean()
                                st.metric("Average", f"${avg:,.2f}")
                        
                        st.success("🔍 **Ready to Search!** Go to the Search & Query section.")
            else:
                st.warning("⚠️ Cannot process: Missing required columns (Description and Amount)")
                st.info("💡 Please check the column mapping above or select columns manually.")
        
        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.info("💡 Try a different file format or check that your file isn't corrupted.")

def render_search_page():
    st.header("🔍 Search & Query Transactions")
    
    if st.session_state.transactions_df.empty:
        st.warning("📤 Please upload and process a file first!")
        return
    
    df = st.session_state.transactions_df
    
    # Smart search
    st.subheader("🔍 Smart Text Search")
    search_term = st.text_input("Search in transaction descriptions:", placeholder="e.g., Starbucks, Amazon, ATM, etc.")
    
    if search_term and 'description' in df.columns:
        # Case-insensitive search
        mask = df['description'].str.contains(search_term, case=False, na=False)
        results = df[mask]
        
        if not results.empty:
            st.success(f"✅ Found {len(results)} transactions matching '{search_term}'")
            
            # Show results
            display_cols = ['date', 'description', 'amount', 'transaction_type']
            available_cols = [col for col in display_cols if col in results.columns]
            
            # Format for display
            display_df = results[available_cols].copy()
            if 'date' in display_df.columns:
                display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
            if 'amount' in display_df.columns:
                display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(display_df, use_container_width=True)
            
            # Summary of search results
            if 'amount' in results.columns:
                total_amount = results['amount'].sum()
                st.info(f"💰 **Total amount for '{search_term}' transactions:** ${total_amount:,.2f}")
        else:
            st.warning(f"❌ No transactions found matching '{search_term}'")
            st.info("💡 Try different keywords or check the exact spelling in your transaction descriptions.")
    
    # Quick search buttons
    st.subheader("⚡ Quick Search")
    st.write("**Common search terms:**")
    
    if 'description' in df.columns:
        # Extract common merchants from data
        descriptions = df['description'].str.upper().str.split().explode()
        common_terms = descriptions.value_counts().head(10).index.tolist()
        
        # Create buttons for common terms
        cols = st.columns(5)
        for i, term in enumerate(common_terms[:10]):
            if len(term) > 3:  # Only show meaningful terms
                with cols[i % 5]:
                    if st.button(term, key=f"search_{term}"):
                        # Auto-fill search box
                        st.rerun()
    
    # Amount filter
    st.subheader("💰 Filter by Amount Range")
    if 'amount' in df.columns:
        col1, col2 = st.columns(2)
        with col1:
            min_amount = st.number_input("Minimum amount:", value=float(df['amount'].min()))
        with col2:
            max_amount = st.number_input("Maximum amount:", value=float(df['amount'].max()))
        
        if st.button("Apply Amount Filter"):
            filtered = df[(df['amount'] >= min_amount) & (df['amount'] <= max_amount)]
            st.success(f"✅ Found {len(filtered)} transactions between ${min_amount:,.2f} and ${max_amount:,.2f}")
            
            if not filtered.empty:
                display_cols = ['date', 'description', 'amount', 'transaction_type']
                available_cols = [col for col in display_cols if col in filtered.columns]
                
                display_df = filtered[available_cols].copy()
                if 'date' in display_df.columns:
                    display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
                if 'amount' in display_df.columns:
                    display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(display_df, use_container_width=True)

def render_analytics_page():
    st.header("📊 Analytics Dashboard")
    
    if st.session_state.transactions_df.empty:
        st.warning("📤 Please upload data first!")
        return
    
    df = st.session_state.transactions_df
    
    # Key metrics
    if 'amount' in df.columns:
        st.subheader("📈 Financial Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            income = df[df['amount'] > 0]['amount'].sum() if (df['amount'] > 0).any() else 0
            st.metric("💰 Total Income", f"${income:,.2f}")
        
        with col2:
            expenses = abs(df[df['amount'] < 0]['amount'].sum()) if (df['amount'] < 0).any() else 0
            st.metric("💸 Total Expenses", f"${expenses:,.2f}")
        
        with col3:
            net = income - expenses
            st.metric("🏦 Net Amount", f"${net:,.2f}")
        
        with col4:
            avg_transaction = df['amount'].mean()
            st.metric("📊 Avg Transaction", f"${avg_transaction:,.2f}")
    
    # Transaction breakdown
    st.subheader("🔍 Transaction Analysis")
    
    if 'transaction_type' in df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Transaction Type Breakdown:**")
            type_counts = df['transaction_type'].value_counts()
            for t_type, count in type_counts.items():
                st.write(f"• {t_type}: {count} transactions")
        
        with col2:
            if 'description' in df.columns:
                st.write("**Most Frequent Merchants:**")
                # Get top merchants (expenses only)
                expenses = df[df['amount'] < 0] if (df['amount'] < 0).any() else pd.DataFrame()
                if not expenses.empty:
                    top_merchants = expenses['description'].value_counts().head(5)
                    for merchant, count in top_merchants.items():
                        st.write(f"• {merchant}: {count} times")
    
    # Raw data view
    st.subheader("📋 All Transactions")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox("Filter by type:", ["All", "Income", "Expenses"])
    with col2:
        sort_by = st.selectbox("Sort by:", ["Date (newest first)", "Amount (highest first)", "Description"])
    with col3:
        show_rows = st.selectbox("Show rows:", [10, 25, 50, 100, "All"])
    
    # Apply filters and sorting
    filtered_df = df.copy()
    
    if filter_type == "Income" and 'amount' in df.columns:
        filtered_df = filtered_df[filtered_df['amount'] > 0]
    elif filter_type == "Expenses" and 'amount' in df.columns:
        filtered_df = filtered_df[filtered_df['amount'] < 0]
    
    # Apply sorting
    if sort_by == "Date (newest first)" and 'date' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('date', ascending=False)
    elif sort_by == "Amount (highest first)" and 'amount' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('amount', ascending=False)
    elif sort_by == "Description" and 'description' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('description')
    
    # Limit rows
    if show_rows != "All":
        filtered_df = filtered_df.head(show_rows)
    
    # Prepare display
    display_cols = ['date', 'description', 'amount', 'transaction_type']
    available_cols = [col for col in display_cols if col in filtered_df.columns]
    
    if available_cols:
        display_df = filtered_df[available_cols].copy()
        
        # Format for display
        if 'date' in display_df.columns:
            display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
        if 'amount' in display_df.columns:
            display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(display_df, use_container_width=True, height=400)
    else:
        st.warning("No data available to display")

if __name__ == "__main__":
    main()