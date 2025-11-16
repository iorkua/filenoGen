"""
Production File Number Generation with Enhanced Monitoring
Run this script to generate all 7.2M file numbers with real-time progress tracking
"""

import sys
import os
import time
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from production_insertion import ProductionInserter

def run_production_with_monitoring():
    """Run production generation with enhanced monitoring"""
    
    print("=" * 70)
    print("FILE NUMBER PRODUCTION GENERATION")
    print("=" * 70)
    print()
    
    print("Configuration Summary:")
    print("- Total Records: 7,200,000")
    print("- Categories: 16 (RES, COM, IND, AG, RES-RC, COM-RC, IND-RC, AG-RC, CON-RES, CON-COM, CON-IND, CON-AG, CON-RES-RC, CON-COM-RC, CON-IND-RC, CON-AG-RC)")
    print("- Years: 1981-2025 (45 years)")
    print("- Numbers per year per category: 10,000")
    print("- Batch size: 1,000 records")
    print("- Transaction size: 10,000 records")
    print()
    
    print("New Features:")
    print("- Tracking ID generation: TRK-XXXXXXXX-XXXXX format")
    print("- Updated registry format: 1, 2, 3 (instead of Registry 1/2/3)")
    print("- Group/sys_batch numbering maintained plus registry_batch_no per registry")
    print()
    
    print("Estimated Performance:")
    print("- Processing speed: ~1,800 records/second")
    print("- Estimated total time: ~65 minutes")
    print("- Memory usage: <500MB")
    print()
    
    # Confirm before starting
    response = input("Do you want to start the production generation? (y/N): ")
    if response.lower() != 'y':
        print("Production generation cancelled.")
        return
    
    print()
    print("=" * 70)
    print("STARTING PRODUCTION GENERATION...")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # Create and run the production inserter
        inserter = ProductionInserter()
        success = inserter.run_production_insertion()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print()
        print("=" * 70)
        
        if success:
            print("✓ PRODUCTION GENERATION COMPLETED SUCCESSFULLY!")
            print()
            print(f"Final Statistics:")
            print(f"- Total records processed: {inserter.processed_records:,}")
            print(f"- Categories completed: {inserter.categories_completed}/{inserter.total_categories}")
            print(f"- Total duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            print(f"- Average speed: {inserter.processed_records/duration:.0f} records/second")
            print()
            print("All 7.2M file numbers have been generated with:")
            print("- Unique tracking IDs (TRK-XXXXXXXX-XXXXX)")
            print("- Updated registry format (1, 2, 3)")
            print("- Proper group and batch numbering")
            print()
            print("The database is now ready for production use!")
        else:
            print("✗ PRODUCTION GENERATION FAILED!")
            print("Check the logs for error details.")
            
        print("=" * 70)
        
    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("PRODUCTION GENERATION INTERRUPTED BY USER")
        print("=" * 70)
        print("Note: Partial data may have been inserted.")
        print("You can restart the process - it will continue from where it left off.")
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"PRODUCTION GENERATION ERROR: {str(e)}")
        print("=" * 70)
        print("Check the logs for detailed error information.")

if __name__ == "__main__":
    run_production_with_monitoring()