import streamlit as st
import pandas as pd
import sys
from pathlib import Path

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
        else:
            st.warning("No data loaded")
    
    # Main content
    if page == "📁 Upload & Process":
        render_upload_page()
    elif page == "🔍 Search & Query":
        render_search_page()
    elif page == "📊 Analytics":
        render_analytics_page()

def render_upload_page():
    st.header("📁 Upload & Process Bank Statements")
    
    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ File uploaded! {len(df)} rows found.")
            
            # Basic processing
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            # Store in session
            st.session_state.transactions_df = df
            
            # Show preview
            st.subheader("📋 Data Preview")
            st.dataframe(df.head(10))
            
            # Basic stats
            if 'amount' in df.columns:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Transactions", len(df))
                with col2:
                    total = df['amount'].sum() if not df['amount'].isna().all() else 0
                    st.metric("Total Amount", f"${total:,.2f}")
                with col3:
                    avg = df['amount'].mean() if not df['amount'].isna().all() else 0
                    st.metric("Average", f"${avg:,.2f}")
                
                st.success("🔍 **Ready!** Go to Search & Query to find transactions.")
        
        except Exception as e:
            st.error(f"Error processing file: {e}")

def render_search_page():
    st.header("🔍 Search & Query Transactions")
    
    if st.session_state.transactions_df.empty:
        st.warning("Please upload a file first!")
        return
    
    df = st.session_state.transactions_df
    
    # Basic search
    search_term = st.text_input("Search in descriptions (basic text search):")
    
    if search_term:
        if 'description' in df.columns:
            mask = df['description'].str.contains(search_term, case=False, na=False)
            results = df[mask]
            
            st.write(f"Found {len(results)} matching transactions:")
            if not results.empty:
                st.dataframe(results)
        else:
            st.warning("No description column found")
    
    # Amount filter
    st.subheader("💰 Filter by Amount")
    if 'amount' in df.columns and not df['amount'].isna().all():
        col1, col2 = st.columns(2)
        with col1:
            min_amount = st.number_input("Minimum amount:", value=float(df['amount'].min()))
        with col2:
            max_amount = st.number_input("Maximum amount:", value=float(df['amount'].max()))
        
        if st.button("Apply Filter"):
            filtered = df[(df['amount'] >= min_amount) & (df['amount'] <= max_amount)]
            st.write(f"Found {len(filtered)} transactions in range:")
            st.dataframe(filtered)

def render_analytics_page():
    st.header("📊 Analytics")
    
    if st.session_state.transactions_df.empty:
        st.warning("Please upload data first!")
        return
    
    df = st.session_state.transactions_df
    
    # Basic metrics
    if 'amount' in df.columns:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            income = df[df['amount'] > 0]['amount'].sum() if (df['amount'] > 0).any() else 0
            st.metric("💰 Total Income", f"${income:,.2f}")
        
        with col2:
            expenses = abs(df[df['amount'] < 0]['amount'].sum()) if (df['amount'] < 0).any() else 0
            st.metric("💸 Total Expenses", f"${expenses:,.2f}")
        
        with col3:
            net = income - expenses
            st.metric("🏦 Net Amount", f"${net:,.2f}")
    
    # Show all data
    st.subheader("📋 All Transactions")
    st.dataframe(df)

if __name__ == "__main__":
    main()
