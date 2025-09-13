import streamlit as st
import pandas as pd

st.set_page_config(page_title="Column Debug", layout="wide")

st.title("🔧 Column Debug Tool")

uploaded_file = st.file_uploader("Upload your Excel/CSV file", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    try:
        # Read the file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success(f"✅ File loaded! {len(df)} rows, {len(df.columns)} columns")
        
        # Show column names
        st.subheader("📋 Your Column Names:")
        st.write("**Columns in your file:**")
        for i, col in enumerate(df.columns):
            st.write(f"{i+1}. `{col}`")
        
        # Show sample data
        st.subheader("📊 Sample Data:")
        st.dataframe(df.head())
        
        # Show data types
        st.subheader("🔍 Column Types:")
        for col in df.columns:
            st.write(f"**{col}:** {df[col].dtype}")
        
    except Exception as e:
        st.error(f"Error: {e}")
