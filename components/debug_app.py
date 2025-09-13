import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

st.title("🔧 Debug Test")

try:
    from components.ui import setup_page_config
    st.success("✅ UI imports work")
    setup_page_config()
    st.success("✅ setup_page_config works")
except Exception as e:
    st.error(f"❌ UI error: {e}")

try:
    from components.upload import FileUploader
    st.success("✅ Upload imports work")
    uploader = FileUploader()
    st.success("✅ FileUploader created")
except Exception as e:
    st.error(f"❌ Upload error: {e}")

try:
    from components.search import BankStatementRAG
    st.success("✅ Search imports work")
    rag = BankStatementRAG()
    st.success("✅ BankStatementRAG created")
except Exception as e:
    st.error(f"❌ Search error: {e}")

try:
    from config.settings import PROJECT_ROOT
    st.success("✅ Config imports work")
    st.write(f"Project root: {PROJECT_ROOT}")
except Exception as e:
    st.error(f"❌ Config error: {e}")

st.write("If you see this, basic functionality is working!")