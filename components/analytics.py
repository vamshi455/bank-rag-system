import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

class AnalyticsDashboard:
    def __init__(self, transactions_df):
        self.df = transactions_df.copy()
        self.filtered_df = transactions_df.copy()
    
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
        if self.filtered_df.empty:
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
            delta_color = "normal" if net_amount >= 0 else "inverse"
            st.metric("🏦 Net Amount", f"${net_amount:,.2f}", delta=f"${net_amount:,.2f}")
        with col4:
            st.metric("📊 Avg Transaction", f"${avg_transaction:,.2f}")
    
    def _render_charts(self):
        """Render various analytics charts"""
        if self.filtered_df.empty:
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_spending_trend_chart()
        
        with col2:
            self._render_category_pie_chart()
        
        # Monthly comparison
        self._render_monthly_comparison()
    
    def _render_spending_trend_chart(self):
        """Render spending trend over time"""
        st.subheader("💸 Daily Spending Trend")
        
        # Group by date and sum amounts
        daily_data = self.filtered_df.groupby('date').agg({
            'amount': 'sum'
        }).reset_index()
        
        # Separate income and expenses
        daily_data['expenses'] = daily_data['amount'].apply(lambda x: abs(x) if x < 0 else 0)
        daily_data['income'] = daily_data['amount'].apply(lambda x: x if x > 0 else 0)
        
        fig = go.Figure()
        
        # Add expenses line
        fig.add_trace(go.Scatter(
            x=daily_data['date'],
            y=daily_data['expenses'],
            mode='lines+markers',
            name='Expenses',
            line=dict(color='red', width=2)
        ))
        
        # Add income line
        fig.add_trace(go.Scatter(
            x=daily_data['date'],
            y=daily_data['income'],
            mode='lines+markers',
            name='Income',
            line=dict(color='green', width=2)
        ))
        
        fig.update_layout(
            title="Daily Income vs Expenses",
            xaxis_title="Date",
            yaxis_title="Amount ($)",
            height=400,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_category_pie_chart(self):
        """Render category breakdown pie chart"""
        st.subheader("🏷️ Spending by Category")
        
        # Categorize transactions
        self.filtered_df['category'] = self.filtered_df['description'].apply(self._categorize_transaction)
        
        # Only show expenses for pie chart
        expenses = self.filtered_df[self.filtered_df['amount'] < 0].copy()
        expenses['amount'] = expenses['amount'].abs()
        
        if expenses.empty:
            st.info("No expense transactions found in selected period.")
            return
        
        category_spending = expenses.groupby('category')['amount'].sum().reset_index()
        
        fig = px.pie(
            category_spending,
            values='amount',
            names='category',
            title='Expense Categories'
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_monthly_comparison(self):
        """Render monthly spending comparison"""
        st.subheader("📅 Monthly Comparison")
        
        # Group by month
        monthly_data = self.filtered_df.groupby(self.filtered_df['date'].dt.to_period('M')).agg({
            'amount': ['sum', 'count']
        }).round(2)
        
        monthly_data.columns = ['Net Amount', 'Transaction Count']
        monthly_data = monthly_data.reset_index()
        monthly_data['date'] = monthly_data['date'].astype(str)
        
        # Split into income and expenses
        monthly_income = self.filtered_df[self.filtered_df['amount'] > 0].groupby(
            self.filtered_df['date'].dt.to_period('M')
        )['amount'].sum()
        
        monthly_expenses = self.filtered_df[self.filtered_df['amount'] < 0].groupby(
            self.filtered_df['date'].dt.to_period('M')
        )['amount'].sum().abs()
        
        # Create comparison chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Income',
            x=[str(idx) for idx in monthly_income.index],
            y=monthly_income.values,
            marker_color='green'
        ))
        
        fig.add_trace(go.Bar(
            name='Expenses',
            x=[str(idx) for idx in monthly_expenses.index],
            y=monthly_expenses.values,
            marker_color='red'
        ))
        
        fig.update_layout(
            title="Monthly Income vs Expenses",
            xaxis_title="Month",
            yaxis_title="Amount ($)",
            barmode='group',
            height=400,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show data table
        st.subheader("📋 Monthly Summary Table")
        st.dataframe(monthly_data, use_container_width=True)
    
    def _render_category_analysis(self):
        """Render detailed category analysis"""
        if self.filtered_df.empty:
            return
        
        st.subheader("🏷️ Detailed Category Analysis")
        
        # Apply categorization
        self.filtered_df['category'] = self.filtered_df['description'].apply(self._categorize_transaction)
        
        # Category summary
        category_summary = self.filtered_df.groupby('category').agg({
            'amount': ['sum', 'count', 'mean'],
            'description': lambda x: x.value_counts().head(1).index[0] if not x.empty else ''
        }).round(2)
        
        category_summary.columns = ['Total Amount', 'Transaction Count', 'Average Amount', 'Top Merchant']
        category_summary = category_summary.sort_values('Total Amount')
        
        # Format the display
        display_summary = category_summary.copy()
        display_summary['Total Amount'] = display_summary['Total Amount'].apply(lambda x: f"${x:,.2f}")
        display_summary['Average Amount'] = display_summary['Average Amount'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(display_summary, use_container_width=True)
        
        # Category insights
        st.subheader("💡 Category Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top spending category
            top_expense_category = category_summary[category_summary['Total Amount'] < 0].nsmallest(1, 'Total Amount')
            if not top_expense_category.empty:
                cat_name = top_expense_category.index[0]
                cat_amount = abs(top_expense_category.iloc[0]['Total Amount'])
                st.info(f"💸 **Highest spending category:** {cat_name} (${cat_amount:,.2f})")
            
            # Most frequent category
            most_frequent_cat = category_summary.nlargest(1, 'Transaction Count')
            if not most_frequent_cat.empty:
                cat_name = most_frequent_cat.index[0]
                cat_count = int(most_frequent_cat.iloc[0]['Transaction Count'])
                st.info(f"🔄 **Most frequent category:** {cat_name} ({cat_count} transactions)")
        
        with col2:
            # Average transaction insights
            highest_avg = category_summary.nlargest(1, 'Average Amount')
            if not highest_avg.empty:
                cat_name = highest_avg.index[0]
                cat_avg = highest_avg.iloc[0]['Average Amount']
                st.info(f"💰 **Highest average transaction:** {cat_name} (${abs(cat_avg):,.2f})")
            
            # Category with most variance
            category_std = self.filtered_df.groupby('category')['amount'].std().fillna(0)
            highest_variance = category_std.nlargest(1)
            if not highest_variance.empty:
                cat_name = highest_variance.index[0]
                st.info(f"📊 **Most variable category:** {cat_name}")
    
    def _categorize_transaction(self, description):
        """Enhanced transaction categorization"""
        desc_lower = description.lower()
        
        # Groceries & Food
        if any(word in desc_lower for word in ['grocery', 'safeway', 'walmart', 'kroger', 'trader joe', 'whole foods', 'costco', 'target']):
            return 'Groceries'
        
        # Restaurants & Dining
        elif any(word in desc_lower for word in ['restaurant', 'cafe', 'starbucks', 'mcdonald', 'pizza', 'burger', 'taco', 'subway', 'chipotle', 'kfc', 'domino']):
            return 'Dining Out'
        
        # Gas & Transportation
        elif any(word in desc_lower for word in ['gas', 'fuel', 'chevron', 'shell', 'exxon', 'uber', 'lyft', 'taxi', 'parking']):
            return 'Transportation'
        
        # Shopping & Retail
        elif any(word in desc_lower for word in ['amazon', 'shopping', 'store', 'mall', 'ebay', 'best buy', 'home depot', 'lowes']):
            return 'Shopping'
        
        # ATM & Banking
        elif any(word in desc_lower for word in ['atm', 'withdrawal', 'bank', 'fee', 'overdraft', 'maintenance']):
            return 'Banking & Fees'
        
        # Entertainment & Subscriptions
        elif any(word in desc_lower for word in ['netflix', 'spotify', 'subscription', 'hulu', 'disney', 'amazon prime', 'youtube']):
            return 'Entertainment'
        
        # Healthcare
        elif any(word in desc_lower for word in ['pharmacy', 'doctor', 'medical', 'hospital', 'cvs', 'walgreens', 'dental']):
            return 'Healthcare'
        
        # Utilities & Bills
        elif any(word in desc_lower for word in ['electric', 'utility', 'phone', 'internet', 'cable', 'water', 'gas bill']):
            return 'Utilities'
        
        # Income & Deposits
        elif any(word in desc_lower for word in ['salary', 'payroll', 'deposit', 'income', 'refund', 'interest', 'dividend']):
            return 'Income'
        
        # Insurance
        elif any(word in desc_lower for word in ['insurance', 'premium', 'policy']):
            return 'Insurance'
        
        # Education
        elif any(word in desc_lower for word in ['school', 'tuition', 'education', 'student', 'book']):
            return 'Education'
        
        else:
            return 'Other'