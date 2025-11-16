"""
Fast Database Update Script - Update all counter fields with progress tracking
Updates: number, group, sys_batch_no, registry_batch_no for all 7.2M records
"""

import pyodbc
import time
from datetime import datetime
from collections import defaultdict

class DatabaseUpdater:
    def __init__(self, connection_string):
        """Initialize database connection"""
        self.conn_string = connection_string
        self.conn = None
        self.cursor = None
        self.records_per_group = 100
        
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = pyodbc.connect(self.conn_string)
            self.cursor = self.conn.cursor()
            print("✓ Connected to database")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Disconnected from database")
    
    def get_total_records(self):
        """Get total number of records in grouping table"""
        try:
            print("  Querying record count...", end=' ', flush=True)
            self.cursor.execute(
                """
                SELECT SUM(row_count)
                FROM sys.dm_db_partition_stats
                WHERE object_id = OBJECT_ID('dbo.grouping')
                  AND index_id IN (0,1)
                """
            )
            total = self.cursor.fetchone()[0] or 0
            print(f"✓ {total:,}")
            return total
        except Exception as e:
            print(f"\n✗ Fast row count failed: {e}")
            print("  ⚠️  Full count may take 30-60 seconds for 7M records...")
            print("  Counting records", end='', flush=True)
            
            # Show progress during count
            start_time = time.time()
            try:
                # Use a more efficient query with sampling for progress indication
                self.cursor.execute("SELECT COUNT(*) FROM grouping WITH (NOLOCK)")
                
                # Show dots while waiting
                import threading
                import sys
                
                def show_dots():
                    while not getattr(show_dots, 'stop', False):
                        print('.', end='', flush=True)
                        time.sleep(2)
                
                dot_thread = threading.Thread(target=show_dots, daemon=True)
                dot_thread.start()
                
                total = self.cursor.fetchone()[0] or 0
                show_dots.stop = True
                
                elapsed = time.time() - start_time
                print(f" ✓ {total:,} (took {elapsed:.1f}s)")
                return total
            except Exception as inner_e:
                print(f"\n✗ Error getting record count: {inner_e}")
                import traceback
                traceback.print_exc()
                return 0
    
    def get_registry_counts(self, show_progress=True):
        """Get record count per registry"""
        try:
            if show_progress:
                print("  Getting registry counts...", end=' ', flush=True)
            
            query = """
            SELECT registry, COUNT(*) as count
            FROM grouping WITH (NOLOCK)
            GROUP BY registry
            ORDER BY registry
            """
            self.cursor.execute(query)
            results = {}
            total = 0
            
            if show_progress:
                print("✓")
            
            for registry, count in self.cursor.fetchall():
                results[registry] = count
                total += count
                print(f"  {registry}: {count:,} records")
            
            if show_progress:
                print(f"  Total: {total:,} records")
            
            return results, total
        except Exception as e:
            print(f"✗ Error getting registry counts: {e}")
            return {}, 0
    
    def update_helper_columns(self):
        """Create helper columns if they don't exist"""
        print("\n📋 Setting up helper columns...")
        try:
            required_columns = {
                'new_number': 'INT',
                'new_group': 'INT',
                'new_sys_batch_no': 'INT',
                'new_registry_batch_no': 'INT'
            }

            self.cursor.execute(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'grouping'
                """
            )
            existing_columns = {row[0].lower() for row in self.cursor.fetchall()}

            for col_name, col_type in required_columns.items():
                if col_name in existing_columns:
                    print(f"  • Column '{col_name}' already exists")
                    continue

                self.cursor.execute(
                    f"ALTER TABLE grouping ADD {col_name} {col_type} NULL"
                )
                self.conn.commit()
                print(f"  ✓ Added column: {col_name}")
        except Exception as e:
            print(f"✗ Error creating columns: {e}")
            return False
        return True
    
    def update_records_by_registry(self, registry_order, registry_sizes):
        """Update records registry by registry using group-based SQL"""
        print("\n🔄 Starting bulk update by registry...\n")

        total_updated = 0
        global_offset = 0
        global_group_counter = 0

        # Process 100 records at a time (one group)
        group_sql = """
            WITH ordered AS (
                SELECT id,
                       ROW_NUMBER() OVER (ORDER BY id) AS rn
                FROM grouping WITH (INDEX(IX_grouping_registry))
                WHERE registry = ?
            )
            UPDATE g
            SET new_number = ordered.rn + ?,
                new_group = ((ordered.rn + ? - 1) / 100) + 1,
                new_sys_batch_no = ((ordered.rn + ? - 1) / 100) + 1,
                new_registry_batch_no = ((ordered.rn - 1) / 100) + 1
            FROM grouping g
            INNER JOIN ordered ON g.id = ordered.id
            WHERE ordered.rn BETWEEN ? AND ?;
        """

        start_all = time.time()

        for registry_idx, registry in enumerate(registry_order, 1):
            registry_size = registry_sizes.get(registry, 0)
            print(f"\n{'='*70}")
            print(f"Processing registry '{registry}' ({registry_idx}/{len(registry_order)})")
            print(f"{'='*70}")

            if registry_size == 0:
                print(f"⚠ No records found for registry '{registry}'")
                continue

            # Calculate groups for this registry
            total_groups = (registry_size + 99) // 100  # Round up to handle partial groups
            print(f"Records to process: {registry_size:,} ({total_groups:,} groups of 100)")
            print(f"Global counter starting at: {global_offset + 1:,}")

            registry_processed = 0
            registry_group = 0
            start = time.time()

            while registry_processed < registry_size:
                # Process exactly 100 records per group
                group_start = registry_processed + 1
                group_end = min(registry_processed + 100, registry_size)
                
                try:
                    self.cursor.execute(
                        group_sql,
                        registry,
                        global_offset,
                        global_offset,
                        global_offset,
                        group_start,
                        group_end
                    )
                    rows = self.cursor.rowcount if self.cursor.rowcount > 0 else (group_end - group_start + 1)
                    self.conn.commit()
                except Exception as e:
                    self.conn.rollback()
                    print(f"✗ Group {registry_group + 1} failed for registry '{registry}': {e}")
                    break

                registry_processed += rows
                total_updated += rows
                registry_group += 1
                global_group_counter += 1

                # Calculate current group and batch numbers
                current_global_number = global_offset + registry_processed
                current_group_number = ((current_global_number - 1) // 100) + 1
                current_registry_batch = registry_group

                elapsed = time.time() - start
                rate = registry_group / elapsed if elapsed > 0 else 0
                remaining_groups = total_groups - registry_group
                eta = remaining_groups / rate if rate > 0 else 0
                eta_str = f"{int(eta // 60)}m {int(eta % 60)}s" if rate > 0 else "calculating..."

                # Progress bar based on groups
                pct = (registry_group / total_groups) * 100
                bar_length = 40
                filled = int(bar_length * registry_group / total_groups)
                bar = '█' * filled + '░' * (bar_length - filled)

                print(
                    f"  [{bar}] Group {registry_group:,}/{total_groups:,} ({pct:.1f}%) | "
                    f"Records: {registry_processed:,}/{registry_size:,} | "
                    f"Global Group: {current_group_number:,} | ETA: {eta_str}",
                    end='\r',
                    flush=True
                )

            global_offset += registry_size
            print()
            print(f"  ✓ Registry '{registry}' updated in {time.time() - start:.1f}s")
            print(f"    Groups processed: {registry_group:,}")
            print(f"    Records processed: {registry_size:,}")
            print(f"    Last global counter: {global_offset:,}")
            print(f"    Last registry_batch_no: {registry_group}")

        elapsed_all = time.time() - start_all
        total_groups = (total_updated + 99) // 100
        print(f"\n{'='*70}")
        print(f"✓ Total records updated: {total_updated:,}")
        print(f"✓ Total groups processed: {total_groups:,}")
        print(f"✓ Time elapsed: {elapsed_all:.1f}s")
        print(f"{'='*70}")
        return total_updated
    
    def verify_calculations(self):
        """Verify the calculated values"""
        print("\n✅ Verifying calculations...\n")
        
        try:
            # Check boundaries
            boundaries = [
                ("Registry 1 - First 5 records", 
                 "SELECT TOP 5 id, new_number, new_group, new_sys_batch_no, new_registry_batch_no FROM grouping WHERE registry='1' ORDER BY id"),
                
                ("Registry 1 → Registry 2 Boundary", 
                 "SELECT TOP 5 id, new_number, new_group, new_sys_batch_no, new_registry_batch_no FROM grouping WHERE id BETWEEN 879998 AND 880002 ORDER BY id"),
                
                ("Registry 2 - First 5 records",
                 "SELECT TOP 5 id, new_number, new_group, new_sys_batch_no, new_registry_batch_no FROM grouping WHERE registry='2' ORDER BY id"),
                
                ("Registry 2 → Registry 3 Boundary",
                 "SELECT TOP 5 id, new_number, new_group, new_sys_batch_no, new_registry_batch_no FROM grouping WHERE id BETWEEN 3599998 AND 3600002 ORDER BY id"),
                
                ("Registry 3 - First 5 records",
                 "SELECT TOP 5 id, new_number, new_group, new_sys_batch_no, new_registry_batch_no FROM grouping WHERE registry='3' ORDER BY id"),
            ]
            
            for label, query in boundaries:
                print(f"📊 {label}")
                self.cursor.execute(query)
                results = self.cursor.fetchall()
                
                for row in results:
                    id_val, num, grp, batch, reg_batch = row
                    print(f"  id={id_val:>7} | num={num:>8,} | grp={grp:>6,} | batch={batch:>6,} | reg_batch={reg_batch:>6,}")
                print()
            
            # Check min/max values
            print("📈 Overall Statistics")
            query = """
            SELECT 
                COUNT(*) as total,
                MIN(new_number) as min_number,
                MAX(new_number) as max_number,
                MIN(new_group) as min_group,
                MAX(new_group) as max_group,
                MIN(new_registry_batch_no) as min_reg_batch,
                MAX(new_registry_batch_no) as max_reg_batch
            FROM grouping
            WHERE new_number IS NOT NULL
            """
            self.cursor.execute(query)
            row = self.cursor.fetchone()
            
            if row:
                total, min_num, max_num, min_grp, max_grp, min_reg, max_reg = row
                print(f"  Total updated: {total:,}")
                print(f"  number: {min_num:,} → {max_num:,}")
                print(f"  group: {min_grp:,} → {max_grp:,}")
                print(f"  registry_batch_no: {min_reg:,} → {max_reg:,}")
            
        except Exception as e:
            print(f"✗ Verification error: {e}")
    
    def apply_updates(self):
        """Apply the calculated values to actual columns"""
        print("\n🔄 Applying updates to actual columns...\n")
        
        try:
            update_query = """
            UPDATE grouping
            SET 
                [number] = CAST(new_number AS VARCHAR(20)),
                [group] = CAST(new_group AS VARCHAR(20)),
                sys_batch_no = CAST(new_sys_batch_no AS VARCHAR(20)),
                registry_batch_no = CAST(new_registry_batch_no AS VARCHAR(20))
            WHERE new_number IS NOT NULL
            """
            
            start = time.time()
            self.cursor.execute(update_query)
            self.cursor.commit()
            elapsed = time.time() - start
            
            # Count updated records
            self.cursor.execute("SELECT COUNT(*) FROM grouping WHERE number IS NOT NULL")
            updated = self.cursor.fetchone()[0]
            
            print(f"✓ Applied updates in {elapsed:.1f}s")
            print(f"✓ Total records with updated values: {updated:,}")
            
            return True
        except Exception as e:
            print(f"✗ Error applying updates: {e}")
            self.cursor.rollback()
            return False
    
    def cleanup_helper_columns(self):
        """Remove helper columns"""
        print("\n🧹 Cleaning up helper columns...\n")
        
        try:
            columns = ['new_number', 'new_group', 'new_sys_batch_no', 'new_registry_batch_no']
            for col in columns:
                self.cursor.execute(f"ALTER TABLE grouping DROP COLUMN {col}")
                self.conn.commit()
                print(f"  ✓ Dropped column: {col}")
            return True
        except Exception as e:
            print(f"✗ Cleanup error: {e}")
            return False
    
    def run_full_update(self):
        """Execute complete update workflow"""
        print("\n" + "="*70)
        print("🚀 FILE NUMBER GENERATOR - DATABASE UPDATE")
        print("="*70)
        
        if not self.connect():
            return False
        
        try:
            # Show current state
            print("\n📊 Current Database State")
            print("-" * 70)
            
            # Try fast count first, but don't hang on slow count
            print("Getting database overview...")
            registry_counts, total_from_registries = self.get_registry_counts()

            if not registry_counts:
                print("❌ No registry data found. Aborting update.")
                return False

            registry_order = sorted(registry_counts.keys(), key=lambda x: int(x))
            
            # Use registry total if main count is taking too long
            print(f"\nFound {len(registry_order)} registries with {total_from_registries:,} total records")
            
            # Confirm before proceeding
            print("\n⚠️  This will update all counter fields:")
            print("   - number (global: 1-7.2M)")
            print("   - group (global: 1-72K)")
            print("   - sys_batch_no (global: 1-72K)")
            print("   - registry_batch_no (per registry resets)")
            
            response = input("\nContinue? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Cancelled")
                return False
            
            # Setup
            if not self.update_helper_columns():
                return False
            
            # Update
            updated = self.update_records_by_registry(registry_order, registry_counts)
            
            if updated > 0:
                # Verify
                self.verify_calculations()
                
                # Apply
                if self.apply_updates():
                    # Cleanup
                    self.cleanup_helper_columns()
                    
                    print("\n" + "="*70)
                    print("✅ DATABASE UPDATE COMPLETE")
                    print("="*70)
                    return True
            
            return False
            
        finally:
            self.disconnect()


if __name__ == "__main__":
    # Configure connection string for your database
    SERVER = "VMI2583396"
    DATABASE = "klas"
    USERNAME = "klas"
    PASSWORD = "YourStrongPassword123!"
    
    connection_string = f"""
    Driver={{ODBC Driver 17 for SQL Server}};
    Server={SERVER};
    Database={DATABASE};
    UID={USERNAME};
    PWD={PASSWORD};
    """
    
    updater = DatabaseUpdater(connection_string)
    success = updater.run_full_update()
    
    if success:
        print("\n✨ All done! Your database has been updated.")
    else:
        print("\n❌ Update failed or cancelled.")
