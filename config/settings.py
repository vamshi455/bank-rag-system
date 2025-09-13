import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_DIR = PROJECT_ROOT / "database"
EXPORTS_DIR = PROJECT_ROOT / "exports"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
for directory in [DATA_DIR, DATABASE_DIR, EXPORTS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# ChromaDB settings
CHROMA_COLLECTION_NAME = "bank_transactions"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Application settings
MAX_FILE_SIZE_MB = 50
SUPPORTED_FORMATS = ['.csv', '.xlsx', '.xls', '.txt']
MAX_TRANSACTIONS_DISPLAY = 100

# UI settings
PAGE_TITLE = "🏦 Bank Statement RAG"
PAGE_ICON = "🏦"
LAYOUT = "wide"