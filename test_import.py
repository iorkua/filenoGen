#!/usr/bin/env python3
"""
Test Excel Import - Process only 10 records for testing
"""

import pandas as pd
import random
import string
from datetime import datetime
import logging
from pathlib import Path
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from database_connection import DatabaseConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_tracking_id():
    """Generate a unique tracking ID in format: TRK-B9010697-C2474"""
    first_part = ''.join(random.choices(string.digits, k=7))
    second_part = ''.join(random.choices(string.digits, k=4))
    return f"TRK-B{first_part}-C{second_part}"

def test_import():
    """Test import with first 10 records."""
    try:
        # Read Excel file
        excel_file = Path("FileNos_Updated.xlsx")
        df = pd.read_excel(excel_file)
        
        # Take only first 10 records for testing
        test_df = df.head(10)
        
        logger.info(f"Testing with {len(test_df)} records")
        
        # Prepare data
        current_time = datetime.now()
        prepared_data = []
        
        for index, row in test_df.iterrows():
            # Combine location info including layout name
            layout_name = str(row['layoutName']) if pd.notna(row['layoutName']) else ''
            location = f"{row['lgaName']}, {row['districtName']}"
            if layout_name:
                location = f"{layout_name}, {location}"
                
            tracking_id = generate_tracking_id()
            
            record = {
                'kangisFileNo': str(row['kangisFileNo']) if pd.notna(row['kangisFileNo']) else None,
                'mlsfNo': str(row['mlsfNo']) if pd.notna(row['mlsfNo']) else None,
                'NewKANGISFileNo': None,
                'FileName': str(row['currentAllottee']) if pd.notna(row['currentAllottee']) else None,
                'created_at': current_time,
                'location': location,
                'created_by': 'Test Import',
                'type': 'KANGIS',  # Set type to indicate source
                'is_deleted': 0,
                'SOURCE': 'KANGIS GIS',
                'plot_no': str(row['plotNo']) if pd.notna(row['plotNo']) else None,
                'tp_no': str(row['tpPlanNo']) if pd.notna(row['tpPlanNo']) else None,
                'tracking_id': tracking_id,
                'date_migrated': str(current_time),
                'migrated_by': '1',
                'migration_source': 'KANGIS GIS'
            }
            prepared_data.append(record)
            
            logger.info(f"Record {index + 1}: {tracking_id} - {record['FileName']}")
        
        # Test database connection
        db = DatabaseConnection()
        if not db.test_connection():
            logger.error("Database connection failed!")
            return False
        
        # Table already exists, no need to create
        conn = db.get_connection()
        cursor = conn.cursor()
        logger.info("Using existing fileNumber table")
        
        # Insert test data (using existing table structure)
        insert_sql = """
        INSERT INTO [dbo].[fileNumber] (
            [kangisFileNo], [mlsfNo], [NewKANGISFileNo], [FileName], [created_at],
            [location], [created_by], [type], [is_deleted],
            [SOURCE], [plot_no], [tp_no], [tracking_id], [date_migrated],
            [migrated_by], [migration_source]
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for record in prepared_data:
            values = (
                record['kangisFileNo'],
                record['mlsfNo'],
                record['NewKANGISFileNo'],
                record['FileName'],
                record['created_at'],
                record['location'],
                record['created_by'],
                record['type'],
                record['is_deleted'],
                record['SOURCE'],
                record['plot_no'],
                record['tp_no'],
                record['tracking_id'],
                record['date_migrated'],
                record['migrated_by'],
                record['migration_source']
            )
            cursor.execute(insert_sql, values)
        
        conn.commit()
        logger.info(f"Successfully inserted {len(prepared_data)} test records")
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM [dbo].[fileNumber] WHERE [created_by] = 'Test Import'")
        count = cursor.fetchone()[0]
        logger.info(f"Verification: {count} test records found in database")
        
        # Show sample records
        cursor.execute("SELECT TOP 3 [tracking_id], [FileName], [location] FROM [dbo].[fileNumber] WHERE [created_by] = 'Test Import'")
        sample_records = cursor.fetchall()
        
        logger.info("Sample inserted records:")
        for record in sample_records:
            logger.info(f"  {record[0]} - {record[1]}")
            logger.info(f"    Location: {record[2]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Test import failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Excel Import with 10 records...")
    success = test_import()
    if success:
        print("✅ Test import successful!")
    else:
        print("❌ Test import failed!")