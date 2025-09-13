import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
import json
from pathlib import Path
from config.settings import DATABASE_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL

class BankStatementRAG:
    def __init__(self):
        self.client = None
        self.collection = None
        self.transactions_df = pd.DataFrame()
        self._initialize_chromadb()
    
    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(path=str(DATABASE_DIR))
            
            # Initialize embedding function
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
            
            # Try to get existing collection or create new one
            try:
                self.collection = self.client.get_collection(
                    name=CHROMA_COLLECTION_NAME,
                    embedding_function=self.embedding_function
                )
                st.sidebar.success("✅ Connected to existing database")
            except:
                self.collection = self.client.create_collection(
                    name=CHROMA_COLLECTION_NAME,
                    embedding_function=self.embedding_function
                )
                st.sidebar.info("🆕 Created new database")
                
        except Exception as e:
            st.error(f"Failed to initialize ChromaDB: {str(e)}")
    
    def index_transactions(self, transactions_df):
        """Index transactions in ChromaDB for semantic search"""
        self.transactions_df = transactions_df.copy()
        
        if transactions_df.empty:
            return False
        
        try:
            with st.spinner("🔄 Creating semantic search index..."):
                # Clear existing data
                try:
                    self.client.delete_collection(CHROMA_COLLECTION_NAME)
                except:
                    pass
                
                # Create fresh collection
                self.collection = self.client.create_collection(
                    name=CHROMA_COLLECTION_NAME,
                    embedding_function=self.embedding_function
                )
                
                # Prepare documents for embedding
                documents = []
                metadatas = []
                ids = []
                
                for idx, row in transactions_df.iterrows():
                    # Create rich document for embedding
                    doc = self._create_document_text(row)
                    documents.append(doc)
                    
                    # Create metadata
                    metadata = {
                        "date": str(row['date'].date()),
                        "description": row['description'],
                        "amount": float(row['amount']),
                        "month": str(row['month']),
                        "year": int(row['year']),
                        "transaction_type": row['transaction_type'],
                        "source_file": row['source_file'],
                        "day_of_week": row['day_of_week'],
                        "is_weekend": bool(row['is_weekend'])
                    }
                    metadatas.append(metadata)
                    ids.append(f"tx_{idx}")
                
                # Add to ChromaDB in batches to avoid memory issues
                batch_size = 100
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i+batch_size]
                    batch_metadata = metadatas[i:i+batch_size]
                    batch_ids = ids[i:i+batch_size]
                    
                    self.collection.add(
                        documents=batch_docs,
                        metadatas=batch_metadata,
                        ids=batch_ids
                    )
                
                st.success(f"✅ Indexed {len(documents)} transactions for semantic search")
                return True
                
        except Exception as e:
            st.error(f"Failed to index transactions: {str(e)}")
            return False
    
    def _create_document_text(self, row):
        """Create rich text document for embedding"""
        # Create descriptive text that includes context
        amount_desc = "income" if row['amount'] > 0 else "expense"
        amount_size = "large" if abs(row['amount']) > 100 else "small"
        
        doc = f"""
        Transaction: {row['description']}
        Amount: ${row['amount']:.2f} ({amount_desc}, {amount_size})
        Date: {row['date'].strftime('%B %d, %Y')} ({row['day_of_week']})
        Month: {row['date'].strftime('%B %Y')}
        Type: {row['transaction_type']}
        Weekend: {'yes' if row['is_weekend'] else 'no'}
        """.strip()
        
        return doc
    
    def search(self, query, n_results=20, filters=None):
        """Search transactions using natural language query"""
        if not self.collection:
            st.error("Database not initialized. Please upload and process files first.")
            return pd.DataFrame()
        
        try:
            # Extract filters from query
            extracted_filters = self._extract_query_filters(query)
            if filters:
                extracted_filters.update(filters)
            
            # Build ChromaDB query
            where_clause = self._build_where_clause(extracted_filters)
            
            # Perform semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, 100),  # Limit for performance
                where=where_clause if where_clause else None
            )
            
            if not results['ids'] or not results['ids'][0]:
                return pd.DataFrame()
            
            # Convert results back to DataFrame
            result_df = self._results_to_dataframe(results)
            
            # Apply additional filtering based on query
            result_df = self._apply_query_filters(result_df, query, extracted_filters)
            
            return result_df
            
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            return pd.DataFrame()
    
    def _extract_query_filters(self, query):
        """Extract filters from natural language query"""
        filters = {}
        query_lower = query.lower()
        
        # Extract amount filters
        amount_patterns = [
            (r'over\s+\$?(\d+(?:,\d+)*(?:\.\d{2})?)', 'amount_min'),
            (r'above\s+\$?(\d+(?:,\d+)*(?:\.\d{2})?)', 'amount_min'),
            (r'more\s+than\s+\$?(\d+(?:,\d+)*(?:\.\d{2})?)', 'amount_min'),
            (r'under\s+\$?(\d+(?:,\d+)*(?:\.\d{2})?)', 'amount_max'),
            (r'below\s+\$?(\d+(?:,\d+)*(?:\.\d{2})?)', 'amount_max'),
            (r'less\s+than\s+\$?(\d+(?:,\d+)*(?:\.\d{2})?)', 'amount_max')
        ]
        
        for pattern, filter_type in amount_patterns:
            match = re.search(pattern, query_lower)
            if match:
                amount = float(match.group(1).replace(',', ''))
                filters[filter_type] = amount
                break
        
        # Extract time filters
        if 'last month' in query_lower:
            last_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
            last_month_end = datetime.now().replace(day=1) - timedelta(days=1)
            filters['date_start'] = last_month_start.date()
            filters['date_end'] = last_month_end.date()
        
        elif 'this month' in query_lower:
            this_month_start = datetime.now().replace(day=1)
            filters['date_start'] = this_month_start.date()
            filters['date_end'] = datetime.now().date()
        
        elif 'this year' in query_lower:
            year_start = datetime.now().replace(month=1, day=1)
            filters['date_start'] = year_start.date()
            filters['date_end'] = datetime.now().date()
        
        elif 'last year' in query_lower:
            last_year = datetime.now().year - 1
            filters['year'] = last_year
        
        # Extract transaction type
        if any(word in query_lower for word in ['income', 'deposit', 'salary', 'credit']):
            filters['transaction_type'] = 'Credit'
        elif any(word in query_lower for word in ['expense', 'spending', 'purchase', 'debit']):
            filters['transaction_type'] = 'Debit'
        
        return filters
    
    def _build_where_clause(self, filters):
        """Build ChromaDB where clause from filters"""
        if not filters:
            return None
        
        where_conditions = []
        
        # Amount filters
        if 'amount_min' in filters:
            where_conditions.append({"amount": {"$gte": filters['amount_min']}})
        if 'amount_max' in filters:
            where_conditions.append({"amount": {"$lte": filters['amount_max']}})
        
        # Date filters
        if 'date_start' in filters:
            where_conditions.append({"date": {"$gte": str(filters['date_start'])}})
        if 'date_end' in filters:
            where_conditions.append({"date": {"$lte": str(filters['date_end'])}})
        
        # Year filter
        if 'year' in filters:
            where_conditions.append({"year": filters['year']})
        
        # Transaction type filter
        if 'transaction_type' in filters:
            where_conditions.append({"transaction_type": filters['transaction_type']})
        
        # Combine conditions with AND
        if len(where_conditions) == 1:
            return where_conditions[0]
        elif len(where_conditions) > 1:
            return {"$and": where_conditions}
        
        return None
    
    def _apply_query_filters(self, df, query, filters):
        """Apply additional filters that couldn't be handled by ChromaDB"""
        if df.empty:
            return df
        
        # Convert metadata back to proper types
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = df['amount'].astype(float)
        
        # Apply amount filters if they exist
        if 'amount_min' in filters:
            df = df[abs(df['amount']) >= filters['amount_min']]
        if 'amount_max' in filters:
            df = df[abs(df['amount']) <= filters['amount_max']]
        
        return df
    
    def _results_to_dataframe(self, results):
        """Convert ChromaDB results to pandas DataFrame"""
        if not results['metadatas'] or not results['metadatas'][0]:
            return pd.DataFrame()
        
        # Extract metadata
        metadata_list = results['metadatas'][0]
        distances = results['distances'][0] if results.get('distances') else [0] * len(metadata_list)
        
        # Create DataFrame
        df = pd.DataFrame(metadata_list)
        df['similarity_score'] = [1 - d for d in distances]  # Convert distance to similarity
        
        # Sort by similarity
        df = df.sort_values('similarity_score', ascending=False)
        
        return df

class SearchInterface:
    def __init__(self, rag_system):
        self.rag_system = rag_system
        self.query_history = []
    
    def render_search_interface(self):
        """Render the search interface"""
        st.subheader("🔍 Smart Search")
        
        # Search container
        with st.container():
            # Query input
            query = st.text_area(
                "Ask about your transactions:",
                placeholder="e.g., 'Show me restaurant expenses over $50 last month'",
                height=100,
                help="Use natural language to search your transactions. Try asking about amounts, dates, categories, or specific merchants."
            )
            
            # Search options
            col1, col2 = st.columns([3, 1])
            with col1:
                max_results = st.slider("Max results", min_value=10, max_value=100, value=20)
            with col2:
                search_button = st.button("🔍 Search", type="primary", use_container_width=True)
            
            # Example queries
            self._show_example_queries()
            
            # Perform search
            if search_button and query.strip():
                self._perform_search(query, max_results)
            elif search_button:
                st.warning("Please enter a search query.")
    
    def _show_example_queries(self):
        """Show example query buttons"""
        st.markdown("**💡 Quick Examples:**")
        
        examples = [
            "Show me all restaurant expenses",
            "What did I spend over $100 on?",
            "Find ATM withdrawals last month",
            "Show grocery spending this year",
            "Income deposits this month"
        ]
        
        cols = st.columns(len(examples))
        for i, example in enumerate(examples):
            with cols[i]:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    st.session_state.search_query = example
                    st.rerun()
        
        # Handle example query selection
        if hasattr(st.session_state, 'search_query'):
            query = st.session_state.search_query
            del st.session_state.search_query
            self._perform_search(query, 20)
    
    def _perform_search(self, query, max_results):
        """Perform search and display results"""
        with st.spinner("Searching transactions..."):
            results = self.rag_system.search(query, n_results=max_results)
            
            if results.empty:
                st.warning("No matching transactions found. Try rephrasing your query or using different keywords.")
                return
            
            # Add to query history
            self.query_history.append({
                'query': query,
                'results_count': len(results),
                'timestamp': datetime.now()
            })
            
            # Display results
            self._display_search_results(query, results)
    
    def _display_search_results(self, query, results_df):
        """Display search results with summary and details"""
        # Results summary
        st.success(f"Found {len(results_df)} matching transactions")
        
        # Summary metrics
        total_amount = results_df['amount'].sum()
        avg_amount = results_df['amount'].mean()
        date_range = f"{results_df['date'].min().strftime('%Y-%m-%d')} to {results_df['date'].max().strftime('%Y-%m-%d')}"
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Results", len(results_df))
        with col2:
            st.metric("Total Amount", f"${total_amount:,.2f}")
        with col3:
            st.metric("Average", f"${avg_amount:,.2f}")
        with col4:
            st.metric("Date Range", date_range)
        
        # Results table
        st.subheader("📋 Search Results")
        
        # Prepare display dataframe
        display_df = results_df.copy()
        display_df['Date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
        display_df['Description'] = display_df['description']
        display_df['Amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
        display_df['Type'] = display_df['transaction_type']
        display_df['Relevance'] = display_df['similarity_score'].apply(lambda x: f"{x:.2f}")
        
        # Select columns to display
        columns_to_show = ['Date', 'Description', 'Amount', 'Type', 'Relevance']
        st.dataframe(
            display_df[columns_to_show],
            use_container_width=True,
            height=400
        )
        
        # Export options
        self._show_export_options(query, results_df)
    
    def _show_export_options(self, query, results_df):
        """Show export options for search results"""
        st.subheader("📤 Export Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV export
            csv = results_df.to_csv(index=False)
            st.download_button(
                "📄 Download CSV",
                csv,
                f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )
        
        with col2:
            # Excel export
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                results_df.to_excel(writer, sheet_name='Search Results', index=False)
                
                # Add summary sheet
                summary_data = {
                    'Query': [query],
                    'Results Count': [len(results_df)],
                    'Total Amount': [results_df['amount'].sum()],
                    'Average Amount': [results_df['amount'].mean()],
                    'Search Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            st.download_button(
                "📊 Download Excel",
                buffer.getvalue(),
                f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col3:
            # Generate summary report
            if st.button("📝 Generate Report"):
                self._generate_summary_report(query, results_df)
    
    def _generate_summary_report(self, query, results_df):
        """Generate a summary report of search results"""
        st.subheader("📊 Summary Report")
        
        # Create analysis
        report = f"""
        ## Search Query Analysis
        **Query:** "{query}"
        **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        ### Key Findings
        - **Total Transactions:** {len(results_df)}
        - **Total Amount:** ${results_df['amount'].sum():,.2f}
        - **Average Transaction:** ${results_df['amount'].mean():.2f}
        - **Date Range:** {results_df['date'].min().strftime('%Y-%m-%d')} to {results_df['date'].max().strftime('%Y-%m-%d')}
        
        ### Transaction Breakdown
        - **Credits (Income):** {len(results_df[results_df['amount'] > 0])} transactions, ${results_df[results_df['amount'] > 0]['amount'].sum():,.2f}
        - **Debits (Expenses):** {len(results_df[results_df['amount'] < 0])} transactions, ${abs(results_df[results_df['amount'] < 0]['amount'].sum()):,.2f}
        
        ### Top Transactions
        """
        
        # Add top transactions
        top_transactions = results_df.nlargest(5, 'amount')[['date', 'description', 'amount']]
        for _, row in top_transactions.iterrows():
            report += f"- {row['date'][:10]}: {row['description']} - ${row['amount']:,.2f}\n"
        
        st.markdown(report)
        
        # Download report
        st.download_button(
            "📄 Download Report",
            report,
            f"search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            "text/markdown"
        )


# Analytics Component
class AnalyticsDashboard:
    def __init__(self, transactions_df):
        self.df = transactions_df
    
    def render_analytics(self):
        """Render analytics dashboard"""
        if self.df.empty:
            st.info("Upload and process transactions to see analytics.")
            return
        
        st.subheader("📊 Transaction Analytics")
        
        # Time period selector
        self._render_time_controls()
        
        # Key metrics
        self._render_key_metrics()
        
        # Charts
        self._render_charts()
        
        # Category analysis
        self._render_category_analysis()
    
    def _render_time_controls(self):
        """Render time period selection controls"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_date = self.df['date'].min().date()
            max_date = self.df['date'].max().date()
            
            start_date = st.date_input(
                "Start Date",
                value=min_date,
                min_value=min_date,
                max_value=max_date
            )
        
        with col2:
            end_date = st.date_input(
                "End Date", 
                value=max_date,
                min_value=min_date,
                max_value=max_date
            )
        
        with col3:
            period_options = ['All Time', 'Last 30 Days', 'Last 90 Days', 'This Year', 'Last Year']
            selected_period = st.selectbox("Quick Select", period_options)
        
        # Apply time filtering
        if selected_period != 'All Time':
            today = datetime.now().date()
            if selected_period == 'Last 30 Days':
                start_date = today - timedelta(days=30)
                end_date = today
            elif selected_period == 'Last 90 Days':
                start_date = today - timedelta(days=90)
                end_date = today
            elif selected_period == 'This Year':
                start_date = datetime(today.year, 1, 1).date()
                end_date = today
            elif selected_period == 'Last Year':
                start_date = datetime(today.year - 1, 1, 1).date()
                end_date = datetime(today.year - 1, 12, 31).date()
        
        # Filter dataframe
        mask = (self.df['date'].dt.date >= start_date) & (self.df['date'].dt.date <= end_date)
        self.filtered_df = self.df.loc[mask]
        
        if self.filtered_df.empty:
            st.warning("No transactions found in the selected date range.")
            return
    
    def _render_key_metrics(self):
        """Render key metrics cards"""
        if not hasattr(self, 'filtered_df') or self.filtered_df.empty:
            return
        
        # Calculate metrics
        total_income = self.filtered_df[self.filtered_df['amount'] > 0]['amount'].sum()
        total_expenses = abs(self.filtered_df[self.filtered_df['amount'] < 0]['amount'].sum())
        net_amount = total_income - total_expenses
        avg_transaction = self.filtered_df['amount'].mean()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Total Income", f"${total_income:,.2f}")
        with col2:
            st.metric("💸 Total Expenses", f"${total_expenses:,.2f}")
        with col3:
            st.metric("🏦 Net Amount", f"${net_amount:,.2f}", delta=f"${net_amount:,.2f}")
        with col4:
            st.metric("📊 Avg Transaction", f"${avg_transaction:,.2f}")
    
    def _render_charts(self):
        """Render various analytics charts"""
        if not hasattr(self, 'filtered_df') or self.filtered_df.empty:
            return
        
        # Spending over time
        from components.ui import create_spending_chart, create_category_chart
        
        col1, col2 = st.columns(2)
        
        with col1:
            spending_chart = create_spending_chart(self.filtered_df)
            if spending_chart:
                st.plotly_chart(spending_chart, use_container_width=True)
        
        with col2:
            category_chart = create_category_chart(self.filtered_df)
            if category_chart:
                st.plotly_chart(category_chart, use_container_width=True)
    
    def _render_category_analysis(self):
        """Render detailed category analysis"""
        if not hasattr(self, 'filtered_df') or self.filtered_df.empty:
            return
        
        st.subheader("🏷️ Category Analysis")
        
        # Categorize transactions (enhanced version)
        def enhanced_categorize(desc):
            desc_lower = desc.lower()
            
            # Groceries
            if any(word in desc_lower for word in ['grocery', 'safeway', 'walmart', 'kroger', 'trader joe', 'whole foods']):
                return 'Groceries'
            
            # Restaurants & Dining
            elif any(word in desc_lower for word in ['restaurant', 'cafe', 'starbucks', 'mcdonald', 'pizza', 'burger', 'taco', 'subway', 'chipotle']):
                return 'Dining'
            
            # Gas & Transportation
            elif any(word in desc_lower for word in ['gas', 'fuel', 'chevron', 'shell', 'uber', 'lyft', 'taxi']):
                return 'Transportation'
            
            # Shopping
            elif any(word in desc_lower for word in ['amazon', 'target', 'shopping', 'store', 'mall', 'ebay']):
                return 'Shopping'
            
            # ATM & Banking
            elif any(word in desc_lower for word in ['atm', 'withdrawal', 'bank', 'fee']):
                return 'Banking'
            
            # Subscriptions & Entertainment
            elif any(word in desc_lower for word in ['netflix', 'spotify', 'subscription', 'hulu', 'disney']):
                return 'Entertainment'
            
            # Healthcare
            elif any(word in desc_lower for word in ['pharmacy', 'doctor', 'medical', 'hospital', 'cvs', 'walgreens']):
                return 'Healthcare'
            
            # Utilities
            elif any(word in desc_lower for word in ['electric', 'utility', 'phone', 'internet', 'cable']):
                return 'Utilities'
            
            # Income
            elif any(word in desc_lower for word in ['salary', 'payroll', 'deposit', 'income', 'refund']):
                return 'Income'
            
            else:
                return 'Other'
        
        # Apply categorization
        self.filtered_df['category'] = self.filtered_df['description'].apply(enhanced_categorize)
        
        # Category summary
        category_summary = self.filtered_df.groupby('category').agg({
            'amount': ['sum', 'count', 'mean']
        }).round(2)
        
        category_summary.columns = ['Total Amount', 'Count', 'Average']
        category_summary = category_summary.sort_values('Total Amount', ascending=False)
        
        st.dataframe(category_summary, use_container_width=True)

# Continue with main app file...