import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

def setup_page_config():
    """Page config is handled in main app - this is just a placeholder"""
    pass

def add_custom_css():
    """Add custom CSS styling"""
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2e86ab 100%);
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        color: #155724;
    }
    
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        color: #721c24;
    }
    
    .info-box {
        background: #cce7ff;
        border: 1px solid #99d6ff;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
        color: #004085;
    }
    
    .upload-zone {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
        background: #fafafa;
    }
    
    .search-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

def show_main_header():
    """Display the main application header"""
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem;">🏦 Bank Statement RAG System</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
            Upload your bank statements and ask intelligent questions about your transactions
        </p>
    </div>
    """, unsafe_allow_html=True)

def show_success_message(message):
    """Display success message"""
    st.markdown(f'<div class="success-box">✅ {message}</div>', unsafe_allow_html=True)

def show_error_message(message):
    """Display error message"""
    st.markdown(f'<div class="error-box">❌ {message}</div>', unsafe_allow_html=True)

def show_info_message(message):
    """Display info message"""
    st.markdown(f'<div class="info-box">ℹ️ {message}</div>', unsafe_allow_html=True)

def create_metric_cards(metrics_data):
    """Create metric cards for dashboard"""
    cols = st.columns(len(metrics_data))
    
    for i, (label, value, delta) in enumerate(metrics_data):
        with cols[i]:
            st.metric(
                label=label,
                value=value,
                delta=delta
            )

def create_spending_chart(transactions_df):
    """Create spending over time chart"""
    if transactions_df.empty:
        return None
    
    # Group by date and sum amounts
    daily_spending = transactions_df.groupby('date')['amount'].sum().reset_index()
    daily_spending = daily_spending.sort_values('date')
    
    fig = px.line(
        daily_spending,
        x='date',
        y='amount',
        title='Daily Spending Trend',
        labels={'amount': 'Amount ($)', 'date': 'Date'}
    )
    
    fig.update_layout(
        showlegend=False,
        height=400,
        template='plotly_white'
    )
    
    return fig

def create_category_chart(transactions_df):
    """Create category breakdown pie chart"""
    if transactions_df.empty:
        return None
    
    # Simple category detection based on description
    def categorize_transaction(desc):
        desc_lower = desc.lower()
        if any(word in desc_lower for word in ['grocery', 'safeway', 'walmart', 'kroger']):
            return 'Groceries'
        elif any(word in desc_lower for word in ['restaurant', 'cafe', 'starbucks', 'mcdonald', 'pizza']):
            return 'Dining'
        elif any(word in desc_lower for word in ['gas', 'fuel', 'chevron', 'shell']):
            return 'Gas'
        elif any(word in desc_lower for word in ['amazon', 'target', 'shopping']):
            return 'Shopping'
        elif any(word in desc_lower for word in ['atm', 'withdrawal']):
            return 'Cash'
        elif any(word in desc_lower for word in ['netflix', 'spotify', 'subscription']):
            return 'Subscriptions'
        else:
            return 'Other'
    
    transactions_df['category'] = transactions_df['description'].apply(categorize_transaction)
    
    # Only show expenses (negative amounts)
    expenses = transactions_df[transactions_df['amount'] < 0].copy()
    expenses['amount'] = expenses['amount'].abs()
    
    category_spending = expenses.groupby('category')['amount'].sum().reset_index()
    
    fig = px.pie(
        category_spending,
        values='amount',
        names='category',
        title='Spending by Category'
    )
    
    fig.update_layout(height=400)
    
    return fig