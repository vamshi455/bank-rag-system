import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# MUST BE FIRST: Set page config before any other streamlit commands
st.set_page_config(
    page_title="🏦 Bank Statement RAG",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# Import components
from components.ui import add_custom_css, show_main_header, show_success_message, show_error_message
from components.upload import FileUploader, show_data_summary
from components.search import BankStatementRAG, SearchInterface
from config.settings import DATABASE_DIR

def main():
    # Add custom CSS
    add_custom_css()
    
    # Initialize session state
    if 'transactions_df' not in st.session_state:
        st.session_state.transactions_df = pd.DataFrame()
    if 'rag_system' not in st.session_state:
        st.session_state.rag_system = BankStatementRAG()
    if 'search_interface' not in st.session_state:
        st.session_state.search_interface = SearchInterface(st.session_state.rag_system)
    
    # Main header
    show_main_header()
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🧭 Navigation")
        page = st.radio(
            "Choose a section:",
            ["📁 Upload & Process", "🔍 Search & Query", "📊 Analytics", "ℹ️ About"],
            index=0
        )
        
        # Show current data status
        st.markdown("---")
        st.subheader("📋 Current Data")
        if not st.session_state.transactions_df.empty:
            st.success(f"✅ {len(st.session_state.transactions_df)} transactions loaded")
            st.info(f"📅 {st.session_state.transactions_df['date'].min().strftime('%Y-%m-%d')} to {st.session_state.transactions_df['date'].max().strftime('%Y-%m-%d')}")
        else:
            st.warning("No data loaded")
        
        # Database status
        st.markdown("---")
        st.subheader("🗄️ Database Status")
        if DATABASE_DIR.exists() and any(DATABASE_DIR.iterdir()):
            st.success("✅ ChromaDB initialized")
        else:
            st.info("🆕 No database yet")
    
    # Main content area
    if page == "📁 Upload & Process":
        render_upload_page()
    elif page == "🔍 Search & Query":
        render_search_page()
    elif page == "📊 Analytics":
        render_analytics_page()
    elif page == "ℹ️ About":
        render_about_page()

def render_upload_page():
    """Render the file upload and processing page"""
    st.header("📁 Upload & Process Bank Statements")
    
    # File uploader
    uploader = FileUploader()
    transactions_df, processing_status = uploader.render_upload_interface()
    
    if transactions_df is not None and not transactions_df.empty:
        # Store in session state
        st.session_state.transactions_df = transactions_df
        
        # Show data summary
        show_data_summary(transactions_df)
        
        # Index transactions for search
        st.subheader("🔄 Creating Search Index")
        with st.spinner("Indexing transactions for semantic search..."):
            success = st.session_state.rag_system.index_transactions(transactions_df)
            if success:
                show_success_message("Transactions indexed successfully! You can now search them.")
                
                # Show quick stats
                st.markdown("### 📈 Quick Overview")
                col1, col2, col3 = st.columns(3)
                with col1:
                    expenses = transactions_df[transactions_df['amount'] < 0]
                    if not expenses.empty:
                        st.metric("💸 Total Expenses", f"${abs(expenses['amount'].sum()):,.2f}")
                    else:
                        st.metric("💸 Total Expenses", "$0.00")
                
                with col2:
                    income = transactions_df[transactions_df['amount'] > 0]
                    if not income.empty:
                        st.metric("💰 Total Income", f"${income['amount'].sum():,.2f}")
                    else:
                        st.metric("💰 Total Income", "$0.00")
                
                with col3:
                    net = transactions_df['amount'].sum()
                    st.metric("🏦 Net Amount", f"${net:,.2f}")
                
                # Ready to search message
                st.success("🔍 **Ready to search!** Go to the 'Search & Query' section to start asking questions about your transactions.")
            else:
                show_error_message("Failed to index transactions. Please try again.")

def render_search_page():
    """Render the search and query page"""
    st.header("🔍 Search & Query Transactions")
    
    if st.session_state.transactions_df.empty:
        st.warning("📤 Please upload and process your bank statements first in the 'Upload & Process' section.")
        st.info("💡 Once you upload files, you'll be able to ask natural language questions about your transactions.")
        return
    
    # Show search interface
    st.session_state.search_interface.render_search_interface()
    
    # Advanced search options
    with st.expander("⚙️ Advanced Search Options"):
        st.subheader("🎛️ Filters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Amount range filter
            st.subheader("💰 Amount Range")
            amount_min = st.number_input("Minimum amount ($)", value=0.0, step=10.0)
            amount_max = st.number_input("Maximum amount ($)", value=10000.0, step=100.0)
            
            # Transaction type filter
            st.subheader("📊 Transaction Type")
            transaction_types = st.multiselect(
                "Select types:",
                options=['Credit', 'Debit'],
                default=['Credit', 'Debit']
            )
        
        with col2:
            # Date range filter
            st.subheader("📅 Date Range")
            if not st.session_state.transactions_df.empty:
                min_date = st.session_state.transactions_df['date'].min().date()
                max_date = st.session_state.transactions_df['date'].max().date()
                
                date_start = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
                date_end = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)
            
            # Source file filter
            st.subheader("📄 Source File")
            if not st.session_state.transactions_df.empty:
                source_files = st.session_state.transactions_df['source_file'].unique()
                selected_files = st.multiselect(
                    "Filter by source file:",
                    options=source_files,
                    default=list(source_files)
                )
        
        # Apply advanced filters button
        if st.button("🔍 Apply Advanced Search"):
            # Build filters dictionary
            filters = {}
            if amount_min > 0:
                filters['amount_min'] = amount_min
            if amount_max < 10000:
                filters['amount_max'] = amount_max
            if len(transaction_types) == 1:
                filters['transaction_type'] = transaction_types[0]
            
            st.info("Advanced filtering applied! Use the search box above to query with these filters.")

def render_analytics_page():
    """Render the analytics dashboard page"""
    st.header("📊 Transaction Analytics")
    
    if st.session_state.transactions_df.empty:
        st.warning("📤 Please upload and process your bank statements first.")
        st.info("💡 Analytics will show spending patterns, trends, and insights from your transaction data.")
        return
    
    df = st.session_state.transactions_df
    
    # Key metrics
    st.subheader("📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_income = df[df['amount'] > 0]['amount'].sum()
        st.metric("💰 Total Income", f"${total_income:,.2f}")
    
    with col2:
        total_expenses = abs(df[df['amount'] < 0]['amount'].sum())
        st.metric("💸 Total Expenses", f"${total_expenses:,.2f}")
    
    with col3:
        net_amount = total_income - total_expenses
        st.metric("🏦 Net Amount", f"${net_amount:,.2f}")
    
    with col4:
        avg_transaction = df['amount'].mean()
        st.metric("📊 Avg Transaction", f"${avg_transaction:,.2f}")
    
    # Transaction breakdown
    st.subheader("🔍 Transaction Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💡 Spending Insights")
        
        # Find largest expense
        expenses = df[df['amount'] < 0]
        if not expenses.empty:
            largest_expense = expenses.nsmallest(1, 'amount').iloc[0]
            st.info(f"💸 **Largest expense:** ${abs(largest_expense['amount']):,.2f} at {largest_expense['description']}")
        
        # Most frequent merchant
        if not expenses.empty:
            most_frequent = expenses['description'].value_counts().head(1)
            if not most_frequent.empty:
                st.info(f"🏪 **Most frequent:** {most_frequent.index[0]} ({most_frequent.iloc[0]} times)")
    
    with col2:
        st.markdown("#### 💰 Income Insights")
        
        # Find largest income
        income = df[df['amount'] > 0]
        if not income.empty:
            largest_income = income.nlargest(1, 'amount').iloc[0]
            st.success(f"💰 **Largest income:** ${largest_income['amount']:,.2f} from {largest_income['description']}")
        
        # Income sources
        if not income.empty:
            income_sources = income['description'].value_counts().head(3)
            st.success("🏦 **Top income sources:**")
            for source, count in income_sources.items():
                st.write(f"  • {source} ({count} times)")
    
    # Show all transactions
    st.subheader("📋 All Transactions")
    
    # Add filters
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.selectbox("Filter by type:", ["All", "Income", "Expenses"])
    with col2:
        sort_by = st.selectbox("Sort by:", ["Date", "Amount", "Description"])
    
    # Apply filters
    filtered_df = df.copy()
    if filter_type == "Income":
        filtered_df = filtered_df[filtered_df['amount'] > 0]
    elif filter_type == "Expenses":
        filtered_df = filtered_df[filtered_df['amount'] < 0]
    
    # Apply sorting
    if sort_by == "Date":
        filtered_df = filtered_df.sort_values('date', ascending=False)
    elif sort_by == "Amount":
        filtered_df = filtered_df.sort_values('amount', ascending=False)
    elif sort_by == "Description":
        filtered_df = filtered_df.sort_values('description')
    
    # Display data
    display_df = filtered_df[['date', 'description', 'amount', 'transaction_type']].copy()
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(display_df, use_container_width=True, height=400)

def render_about_page():
    """Render the about page with usage instructions"""
    st.header("ℹ️ About Bank Statement RAG")
    
    st.markdown("""
    ## 🎯 What is this?
    
    **Bank Statement RAG** is an intelligent system that helps you analyze and search through your bank statements using natural language. Instead of manually scrolling through transactions, you can simply ask questions in plain English!
    
    ## ✨ Key Features
    
    ### 🔍 **Smart Semantic Search**
    - Ask questions like "Show me restaurant expenses over $50"
    - Understands synonyms and context (e.g., "dining out" = restaurants)
    - Powered by ChromaDB and advanced AI embeddings
    
    ### 📊 **Intelligent Analytics** 
    - Automatic spending categorization
    - Visual charts and trends
    - Monthly/yearly comparisons
    - Smart insights and patterns
    
    ### 🔐 **Privacy First**
    - All data processed locally on your machine
    - No data sent to external services
    - Secure ChromaDB storage
    - You control your financial data
    
    ## 🚀 How to Use
    
    ### Step 1: Upload Your Data
    1. Go to **"Upload & Process"** section
    2. Upload CSV, Excel, or text files from your bank
    3. System automatically detects columns and processes data
    4. Wait for indexing to complete
    
    ### Step 2: Search & Query
    1. Go to **"Search & Query"** section  
    2. Type natural language questions:
       - "What did I spend on groceries last month?"
       - "Show me all transactions over $200"
       - "Find ATM withdrawals this year"
       - "What's my average restaurant spending?"
    3. Get intelligent results with context and relevance
    4. Export results to CSV or Excel
    
    ### Step 3: Analyze Trends
    1. Go to **"Analytics"** section
    2. View spending patterns and trends
    3. See category breakdowns and insights
    4. Track income vs expenses over time
    
    ## 🏦 Supported Bank Formats
    
    ### ✅ **Tested Banks:**
    - Chase Bank (CSV exports)
    - Bank of America (CSV/Excel)
    - Wells Fargo (CSV)
    - Citi Bank (CSV)
    - Capital One (CSV)
    - Most credit union exports
    
    ### 📋 **Required Columns:**
    Your bank export should include:
    - **Date**: Transaction date (any format)
    - **Description**: Merchant/transaction details
    - **Amount**: Transaction amount (positive/negative or separate debit/credit columns)
    
    ## 🔧 Technical Details
    
    ### **Architecture:**
    ```
    Streamlit UI ↔ ChromaDB ↔ SentenceTransformers
         ↕              ↕              ↕
    File Processing → Vector Embeddings → Semantic Search
    ```
    
    ### **Technologies Used:**
    - **Frontend**: Streamlit for interactive web interface
    - **Vector Database**: ChromaDB for semantic search
    - **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
    - **Analytics**: Pandas for data analysis
    - **Storage**: Local filesystem, no cloud dependencies
    
    ## 🆘 Troubleshooting
    
    ### **Common Issues:**
    
    **Q: "No valid transactions found"**
    - Check that your CSV has headers in the first row
    - Ensure date column contains valid dates
    - Verify amount column has numeric values
    
    **Q: "Search returns no results"**  
    - Try simpler keywords first
    - Check date ranges in your query
    - Verify data was indexed successfully
    
    **Q: "File upload fails"**
    - Check file size (max 50MB)
    - Ensure file format is CSV, Excel, or TXT
    - Try re-exporting from your bank
    
    ### **Performance Tips:**
    - Larger datasets (>10K transactions) may take longer to index
    - First search after indexing may be slower while models load
    - Close other applications if running low on memory
    
    ## 📈 Next Phase Features
    
    - [ ] Custom transaction categories
    - [ ] Budget tracking and alerts  
    - [ ] Monthly automated reports
    - [ ] Multi-account support
    - [ ] Cloud deployment for team use
    
    ## 💡 Tips for Best Results
    
    ### **Query Examples:**
    - "Show me expenses over $100"
    - "What did I spend last month?"
    - "Find all restaurant expenses"
    - "Large restaurant bills over $50"
    
    ### **Upload Tips:**
    - Download statements covering 3-6 months for best insights
    - Include multiple accounts if desired
    - Rename files descriptively (e.g., "chase_checking_2024.csv")
    
    ---
    
    ## 🎉 Ready to Start?
    
    1. **Upload** your bank statements in the "Upload & Process" section
    2. **Search** your transactions with natural language
    3. **Analyze** your spending patterns and trends
    4. **Export** results and insights for further use
    
    **Need help?** The system provides helpful error messages and suggestions throughout your journey!
    """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.info("Please check your setup and try refreshing the page.")