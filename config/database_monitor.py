#!/usr/bin/env python3
"""
ChromaDB Data Monitor - Track database growth and contents
"""

import os
import sqlite3
from pathlib import Path
import chromadb
from datetime import datetime

def get_directory_size(path):
    """Calculate total size of directory in bytes"""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
    except (OSError, FileNotFoundError):
        pass
    return total

def format_bytes(bytes_size):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def analyze_chromadb():
    """Analyze ChromaDB storage and contents"""
    
    PROJECT_ROOT = Path(__file__).parent
    DATABASE_DIR = PROJECT_ROOT / "database"
    
    print("🔍 ChromaDB Data Analysis")
    print("=" * 50)
    print(f"📍 Database Location: {DATABASE_DIR}")
    print(f"📅 Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if database exists
    if not DATABASE_DIR.exists():
        print("❌ No database directory found!")
        print("💡 Upload some bank statements first to create the database.")
        return
    
    # Calculate total size
    total_size = get_directory_size(DATABASE_DIR)
    print(f"💾 Total Database Size: {format_bytes(total_size)}")
    print()
    
    # List all files in database directory
    print("📂 Database Files:")
    try:
        for item in DATABASE_DIR.rglob("*"):
            if item.is_file():
                size = item.stat().st_size
                relative_path = item.relative_to(DATABASE_DIR)
                print(f"   📄 {relative_path}: {format_bytes(size)}")
    except Exception as e:
        print(f"   ❌ Error listing files: {e}")
    print()
    
    # Connect to ChromaDB and get collection info
    try:
        client = chromadb.PersistentClient(path=str(DATABASE_DIR))
        collections = client.list_collections()
        
        print("🗂️  ChromaDB Collections:")
        if not collections:
            print("   📭 No collections found")
        else:
            for collection in collections:
                print(f"   📊 Collection: {collection.name}")
                try:
                    count = collection.count()
                    print(f"      📈 Documents: {count:,}")
                    
                    # Get sample documents
                    if count > 0:
                        sample = collection.peek(limit=3)
                        print(f"      🔍 Sample IDs: {sample['ids'][:3]}")
                        if sample['metadatas']:
                            print(f"      🏷️  Sample Metadata: {sample['metadatas'][0] if sample['metadatas'][0] else 'None'}")
                except Exception as e:
                    print(f"      ❌ Error getting collection info: {e}")
                print()
                
    except Exception as e:
        print(f"❌ Error connecting to ChromaDB: {e}")
    
    # Check SQLite database if it exists
    sqlite_path = DATABASE_DIR / "chroma.sqlite3"
    if sqlite_path.exists():
        print("🗄️  SQLite Database Info:")
        try:
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print(f"   📋 Tables: {len(tables)}")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"      • {table_name}: {count:,} rows")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Error reading SQLite: {e}")
    
    print("\n" + "=" * 50)

def monitor_growth():
    """Monitor database growth over time"""
    DATABASE_DIR = Path(__file__).parent / "database"
    
    if DATABASE_DIR.exists():
        size = get_directory_size(DATABASE_DIR)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Log to file
        log_file = Path(__file__).parent / "database_growth.log"
        with open(log_file, "a") as f:
            f.write(f"{timestamp},{size},{format_bytes(size)}\n")
        
        print(f"📊 {timestamp}: Database size is {format_bytes(size)}")
    else:
        print("❌ No database found to monitor")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        monitor_growth()
    else:
        analyze_chromadb()