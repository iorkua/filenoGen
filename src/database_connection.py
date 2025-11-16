"""
Database connection helper for SQL Server
Handles connection creation, testing, and connection pool management
"""

import pyodbc
import pymssql
import os
from typing import Optional, Dict, Any
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseConnection:
    """SQL Server database connection manager"""
    
    def __init__(self):
        self.host = os.getenv('DB_SQLSRV_HOST')
        self.port = int(os.getenv('DB_SQLSRV_PORT', 1433))
        self.database = os.getenv('DB_SQLSRV_DATABASE')
        self.username = os.getenv('DB_SQLSRV_USERNAME')
        self.password = os.getenv('DB_SQLSRV_PASSWORD')
        self.connection_timeout = int(os.getenv('CONNECTION_TIMEOUT', 30))
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def get_pyodbc_connection(self) -> Optional[pyodbc.Connection]:
        """
        Create PYODBC connection to SQL Server
        Returns: pyodbc.Connection object or None if failed
        """
        try:
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.host},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"Timeout={self.connection_timeout};"
            )
            
            connection = pyodbc.connect(connection_string)
            self.logger.info("PYODBC connection established successfully")
            return connection
            
        except pyodbc.Error as e:
            self.logger.error(f"PYODBC connection failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error with PYODBC: {e}")
            return None
    
    def get_pymssql_connection(self) -> Optional[pymssql.Connection]:
        """
        Create PyMSSQL connection to SQL Server (alternative driver)
        Returns: pymssql.Connection object or None if failed
        """
        try:
            connection = pymssql.connect(
                server=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                timeout=self.connection_timeout,
                login_timeout=self.connection_timeout,
                as_dict=True
            )
            
            self.logger.info("PyMSSQL connection established successfully")
            return connection
            
        except pymssql.Error as e:
            self.logger.error(f"PyMSSQL connection failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error with PyMSSQL: {e}")
            return None
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test both connection methods and return results
        Returns: Dictionary with connection test results
        """
        results = {
            'pyodbc': False,
            'pymssql': False,
            'preferred': None,
            'errors': []
        }
        
        # Test PYODBC
        pyodbc_conn = self.get_pyodbc_connection()
        if pyodbc_conn:
            try:
                cursor = pyodbc_conn.cursor()
                cursor.execute("SELECT 1 AS test")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    results['pyodbc'] = True
                    results['preferred'] = 'pyodbc'
                cursor.close()
                pyodbc_conn.close()
            except Exception as e:
                results['errors'].append(f"PYODBC test query failed: {e}")
        
        # Test PyMSSQL
        pymssql_conn = self.get_pymssql_connection()
        if pymssql_conn:
            try:
                cursor = pymssql_conn.cursor()
                cursor.execute("SELECT 1 AS test")
                row = cursor.fetchone()
                if row and row['test'] == 1:
                    results['pymssql'] = True
                    if not results['preferred']:
                        results['preferred'] = 'pymssql'
                cursor.close()
                pymssql_conn.close()
            except Exception as e:
                results['errors'].append(f"PyMSSQL test query failed: {e}")
        
        return results
    
    def get_connection(self, preferred_driver: str = 'pyodbc'):
        """
        Get a database connection using the preferred driver
        Args:
            preferred_driver: 'pyodbc' or 'pymssql'
        Returns: Database connection object
        """
        if preferred_driver == 'pyodbc':
            return self.get_pyodbc_connection()
        elif preferred_driver == 'pymssql':
            return self.get_pymssql_connection()
        else:
            self.logger.error(f"Unknown driver: {preferred_driver}")
            return None
    
    def verify_table_structure(self, connection, table_name: str = 'grouping') -> bool:
        """
        Verify that the target table exists and has the expected structure
        Args:
            connection: Database connection
            table_name: Name of the table to verify
        Returns: True if table structure is correct
        """
        try:
            cursor = connection.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo'
            """, table_name)
            
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                self.logger.error(f"Table '{table_name}' does not exist")
                return False
            
            # Check table columns
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo'
                ORDER BY ORDINAL_POSITION
            """, table_name)
            
            columns = cursor.fetchall()
            expected_columns = [
                'id', 'awaiting_fileno', 'created_by', 'number', 'year',
                'landuse', 'created_at', 'registry', 'mls_fileno', 
                'mapping', 'group', 'sys_batch_no', 'registry_batch_no', 'tracking_id'
            ]
            
            actual_columns = [col[0] for col in columns]
            
            missing_columns = set(expected_columns) - set(actual_columns)
            if missing_columns:
                self.logger.error(f"Missing columns: {missing_columns}")
                return False
            
            self.logger.info(f"Table '{table_name}' structure verified successfully")
            cursor.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying table structure: {e}")
            return False


def main():
    """Test the database connection"""
    db = DatabaseConnection()
    
    print("Testing SQL Server connections...")
    print(f"Host: {db.host}")
    print(f"Database: {db.database}")
    print(f"Username: {db.username}")
    print("-" * 50)
    
    # Test connections
    results = db.test_connection()
    
    print(f"PYODBC Connection: {'✓' if results['pyodbc'] else '✗'}")
    print(f"PyMSSQL Connection: {'✓' if results['pymssql'] else '✗'}")
    print(f"Preferred Driver: {results['preferred'] or 'None'}")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    # Test table structure if we have a connection
    if results['preferred']:
        conn = db.get_connection(results['preferred'])
        if conn:
            print(f"\nTesting table structure...")
            table_ok = db.verify_table_structure(conn, 'grouping')
            print(f"Table structure: {'✓' if table_ok else '✗'}")
            conn.close()


if __name__ == "__main__":
    main()