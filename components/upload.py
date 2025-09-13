import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import io
from datetime import datetime
import re

class FileUploader:
    def __init__(self):
        self.supported_formats = ['.csv', '.xlsx', '.xls', '.txt']
        self.max_file_size = 50 * 1024 * 1024  # 50MB in bytes
    
    def render_upload_interface(self):
        """Render the file upload interface"""
        st.subheader("📁 Upload Bank Statements")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose your bank statement files",
            type=['csv', 'xlsx', 'xls', 'txt'],
            accept_multiple_files=True,
            help="Supported formats: CSV, Excel, TXT. Max size: 50MB per file."
        )
        
        if uploaded_files:
            return self.process_uploaded_files(uploaded_files)
        
        # Show example format
        self._show_format_examples()
        
        return None, None
    
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files and return consolidated DataFrame"""
        if st.button("🔄 Process Files", type="primary"):
            
            with st.spinner("Processing uploaded files..."):
                all_transactions = []
                processing_status = []
                
                for file in uploaded_files:
                    try:
                        # Check file size
                        if file.size > self.max_file_size:
                            processing_status.append(f"❌ {file.name}: File too large (max 50MB)")
                            continue
                        
                        # Parse file based on extension
                        transactions = self._parse_file(file)
                        
                        if not transactions.empty:
                            all_transactions.append(transactions)
                            processing_status.append(f"✅ {file.name}: {len(transactions)} transactions loaded")
                        else:
                            processing_status.append(f"⚠️ {file.name}: No valid transactions found")
                            
                    except Exception as e:
                        processing_status.append(f"❌ {file.name}: Error - {str(e)}")
                
                # Show processing results
                for status in processing_status:
                    if status.startswith("✅"):
                        st.success(status)
                    elif status.startswith("⚠️"):
                        st.warning(status)
                    else:
                        st.error(status)
                
                # Combine all transactions
                if all_transactions:
                    combined_df = pd.concat(all_transactions, ignore_index=True)
                    combined_df = self._clean_and_standardize(combined_df)
                    
                    return combined_df, processing_status
                else:
                    st.error("No transactions could be processed from the uploaded files.")
                    return None, processing_status
        
        return None, None
    
    def _parse_file(self, uploaded_file):
        """Parse individual file based on its format"""
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        try:
            if file_extension == '.csv':
                # Try different encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        df = pd.read_csv(uploaded_file, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise Exception("Could not decode CSV file")
                    
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(uploaded_file)
                
            elif file_extension == '.txt':
                # Assume tab-separated or comma-separated
                content = uploaded_file.read().decode('utf-8')
                if '\t' in content:
                    df = pd.read_csv(io.StringIO(content), sep='\t')
                else:
                    df = pd.read_csv(io.StringIO(content))
            else:
                raise Exception(f"Unsupported file format: {file_extension}")
            
            # Reset file pointer for potential re-reading
            uploaded_file.seek(0)
            
            return self._standardize_columns(df, uploaded_file.name)
            
        except Exception as e:
            raise Exception(f"Failed to parse file: {str(e)}")
    
    def _standardize_columns(self, df, filename):
        """Standardize column names and extract required fields"""
        # Convert column names to lowercase for easier matching
        df.columns = df.columns.str.lower().str.strip()
        
        # Find date column
        date_patterns = ['date', 'transaction date', 'posted date', 'trans date', 'posting date']
        date_col = self._find_column(df.columns, date_patterns)
        
        # Find description column
        desc_patterns = ['description', 'desc', 'memo', 'transaction', 'details', 'payee', 'merchant']
        desc_col = self._find_column(df.columns, desc_patterns)
        
        # Find amount column
        amount_patterns = ['amount', 'debit', 'credit', 'transaction amount', 'value', 'sum']
        amount_col = self._find_column(df.columns, amount_patterns)
        
        if not all([date_col, desc_col, amount_col]):
            missing = []
            if not date_col: missing.append("date")
            if not desc_col: missing.append("description") 
            if not amount_col: missing.append("amount")
            raise Exception(f"Could not identify required columns: {', '.join(missing)}")
        
        # Create standardized dataframe
        standardized_df = pd.DataFrame({
            'date': pd.to_datetime(df[date_col], errors='coerce', dayfirst=True),
            'description': df[desc_col].astype(str),
            'amount': pd.to_numeric(df[amount_col].astype(str).str.replace(r'[$,()]', '', regex=True), errors='coerce'),
            'source_file': filename
        })
        
        # Handle debit/credit columns if they exist separately
        if 'debit' in df.columns and 'credit' in df.columns:
            debit = pd.to_numeric(df['debit'], errors='coerce').fillna(0)
            credit = pd.to_numeric(df['credit'], errors='coerce').fillna(0)
            standardized_df['amount'] = credit - debit  # Credits positive, debits negative
        
        # Remove invalid rows
        standardized_df = standardized_df.dropna(subset=['date', 'amount'])
        standardized_df = standardized_df[standardized_df['description'].str.strip() != '']
        
        return standardized_df
    
    def _find_column(self, columns, patterns):
        """Find column name that matches any of the patterns"""
        for pattern in patterns:
            for col in columns:
                if pattern in col:
                    return col
        return None
    
    def _clean_and_standardize(self, df):
        """Clean and standardize the combined DataFrame"""
        # Remove duplicates
        df = df.drop_duplicates(subset=['date', 'description', 'amount'])
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # Clean descriptions
        df['description'] = df['description'].str.strip().str.upper()
        
        # Add useful derived fields
        df['month'] = df['date'].dt.to_period('M')
        df['year'] = df['date'].dt.year
        df['day_of_week'] = df['date'].dt.day_name()
        df['is_weekend'] = df['date'].dt.weekday >= 5
        
        # Add transaction type
        df['transaction_type'] = df['amount'].apply(lambda x: 'Credit' if x > 0 else 'Debit')
        
        return df
    
    def _show_format_examples(self):
        """Show examples of supported file formats"""
        with st.expander("📋 Supported File Formats & Examples"):
            st.markdown("""
            ### CSV Format Example:
            ```
            Date,Description,Amount
            2024-01-15,STARBUCKS #1234,-5.67
            2024-01-15,SALARY DEPOSIT,2500.00
            2024-01-16,GROCERY STORE PURCHASE,-87.45
            ```
            
            ### Common Bank Formats Supported:
            - **Chase Bank**: CSV exports
            - **Bank of America**: CSV/Excel exports
            - **Wells Fargo**: CSV exports
            - **Citi Bank**: CSV exports
            - **Capital One**: CSV exports
            
            ### Required Columns:
            - **Date**: Transaction date (various formats supported)
            - **Description**: Merchant/transaction details
            - **Amount**: Transaction amount (positive for credits, negative for debits)
            
            ### Tips:
            - Ensure your file has headers in the first row
            - Amount should be numeric (remove currency symbols if possible)
            - Date formats are automatically detected
            - Multiple files can be uploaded and will be combined
            """)

def show_data_summary(df):
    """Show summary of loaded data"""
    if df is not None and not df.empty:
        st.subheader("📊 Data Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Transactions", len(df))
        
        with col2:
            net_amount = df['amount'].sum()
            st.metric("Net Amount", f"${net_amount:,.2f}")
        
        with col3:
            date_range = f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}"
            st.metric("Date Range", date_range)
        
        with col4:
            avg_transaction = df['amount'].mean()
            st.metric("Avg Transaction", f"${avg_transaction:,.2f}")
        
        # Show sample data
        with st.expander("🔍 View Sample Data"):
            st.dataframe(df.head(10))