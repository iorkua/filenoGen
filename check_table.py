#!/usr/bin/env python3
"""
Check existing fileNumber table structure
"""

import sys
import os
sys.path.append('src')
from database_connection import DatabaseConnection

def check_table_structure():
    """Check the existing table structure."""
    try:
        db = DatabaseConnection()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'fileNumber'
        """)
        table_exists = cursor.fetchone()[0] > 0
        
        if table_exists:
            print("📋 Existing fileNumber table columns:")
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'fileNumber' 
                ORDER BY ORDINAL_POSITION
            """)
            columns = cursor.fetchall()
            
            for col in columns:
                length = f"({col[2]})" if col[2] else ""
                nullable = "NULL" if col[3] == "YES" else "NOT NULL"
                print(f"  - {col[0]}: {col[1]}{length} {nullable}")
                
            # Check current record count
            cursor.execute("SELECT COUNT(*) FROM fileNumber")
            count = cursor.fetchone()[0]
            print(f"\n📊 Current record count: {count:,}")
            
        else:
            print("❌ fileNumber table does not exist")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking table: {str(e)}")

if __name__ == "__main__":
    check_table_structure()