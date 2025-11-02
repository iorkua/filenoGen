"""
Preview Rack Shelf Labels CSV
Quick preview and analysis of the Rack_Shelf_Labels.csv file before import.
"""

import pandas as pd
import os

def preview_rack_shelf_csv():
    """Preview the structure and content of the Rack Shelf Labels CSV file."""
    csv_file_path = r"c:\Users\Administrator\Documents\filenoGen\Rack_Shelf_Labels.csv"
    
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV file not found: {csv_file_path}")
        return
    
    print("🔍 RACK SHELF LABELS CSV PREVIEW")
    print("=" * 50)
    
    try:
        # Load the CSV file
        df = pd.read_csv(csv_file_path)
        
        print(f"📊 Total Records: {len(df)}")
        print(f"📋 Columns: {list(df.columns)}")
        print()
        
        print("📝 Column Information:")
        print(df.info())
        print()
        
        print("📈 Data Statistics:")
        print(df.describe(include='all'))
        print()
        
        print("🔤 Sample Data (First 10 rows):")
        print(df.head(10))
        print()
        
        print("🔤 Sample Data (Last 5 rows):")
        print(df.tail(5))
        print()
        
        # Check for unique values in key columns
        print("📊 Unique Racks:")
        unique_racks = df['Rack'].unique()
        print(f"Count: {len(unique_racks)}")
        print(f"Values: {sorted(unique_racks)}")
        print()
        
        print("📊 Shelf Range:")
        print(f"Min Shelf: {df['Shelf'].min()}")
        print(f"Max Shelf: {df['Shelf'].max()}")
        print(f"Unique Shelf Count: {df['Shelf'].nunique()}")
        print()
        
        # Check for any missing or duplicate data
        print("⚠️  Data Quality Check:")
        print(f"Missing values:")
        print(df.isnull().sum())
        print()
        
        print(f"Duplicate Full Labels: {df['Full Label'].duplicated().sum()}")
        print(f"Duplicate Rack-Shelf combinations: {df.duplicated(subset=['Rack', 'Shelf']).sum()}")
        print()
        
        # Show some examples of different rack types
        print("📋 Rack Distribution:")
        rack_counts = df['Rack'].value_counts().head(10)
        print(rack_counts)
        
    except Exception as e:
        print(f"❌ Error reading CSV file: {str(e)}")

if __name__ == "__main__":
    preview_rack_shelf_csv()