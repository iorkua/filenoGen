#!/usr/bin/env python3
"""
Preview Excel file structure before import
"""

import pandas as pd
from pathlib import Path

def preview_excel():
    """Preview the Excel file structure and sample data."""
    excel_file = Path("FileNos_Updated.xlsx")
    
    if not excel_file.exists():
        print("❌ Excel file not found!")
        return
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)
        
        print("="*70)
        print("📊 EXCEL FILE PREVIEW - FileNos_Updated.xlsx")
        print("="*70)
        
        print(f"📈 Total Records: {len(df):,}")
        print(f"📋 Total Columns: {len(df.columns)}")
        
        print("\n🔍 COLUMN STRUCTURE:")
        print("-" * 40)
        for i, col in enumerate(df.columns, 1):
            print(f"{i:2d}. {col}")
        
        print("\n📝 SAMPLE DATA (First 5 rows):")
        print("-" * 70)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 30)
        print(df.head())
        
        print("\n📊 DATA SUMMARY:")
        print("-" * 40)
        print(f"Non-null counts:")
        print(df.info())
        
        # Check for expected columns
        expected_columns = [
            'mlsfNo', 'kangisFileNo', 'plotNo', 'tpPlanNo', 
            'currentAllottee', 'layoutName', 'districtName', 'lgaName'
        ]
        
        print("\n✅ COLUMN VALIDATION:")
        print("-" * 40)
        missing_columns = []
        for col in expected_columns:
            if col in df.columns:
                print(f"✓ {col}")
            else:
                print(f"✗ {col} (MISSING)")
                missing_columns.append(col)
        
        if missing_columns:
            print(f"\n❌ Missing columns: {missing_columns}")
            print("Available columns:", list(df.columns))
        else:
            print("\n🎉 All required columns are present!")
            
    except Exception as e:
        print(f"❌ Error reading Excel file: {str(e)}")

if __name__ == "__main__":
    preview_excel()