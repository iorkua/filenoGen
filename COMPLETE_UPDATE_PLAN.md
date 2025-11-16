# Complete Database Update Plan - All Counter Fields

## Objective
Recalculate ALL counter fields (`number`, `group`, `sys_batch_no`, `registry_batch_no`) for every record in the `grouping` table, starting from record 1, using the CORRECT logic.

---

## Counter Definitions (CORRECT)

| Field | Scope | Reset Behavior | Formula | Range |
|-------|-------|---|---|---|
| `number` | GLOBAL | Never | Record position globally (1-7.2M) | 1 → 7,200,000 |
| `group` | GLOBAL | Never | (number - 1) / 100 + 1 | 1 → 72,000 |
| `sys_batch_no` | GLOBAL | Never | Same as `group` (100 per batch) | 1 → 72,000 |
| `registry_batch_no` | PER REGISTRY | Resets per registry | Position within registry / 100 + 1 | Resets: 1→8.8K, 1→27.2K, 1→36K |

---

## Current Problem

**Current database has:**
- ❌ `number`: May be wrong (mixed with per-category logic)
- ❌ `group`: May be wrong (not truly global)
- ❌ `sys_batch_no`: May be wrong (not truly global)
- ❌ `registry_batch_no`: Doesn't reset per registry

**After fix, will have:**
- ✅ `number`: Correct global counter (1-7.2M)
- ✅ `group`: Correct global counter (1-72K)
- ✅ `sys_batch_no`: Correct global counter (1-72K)
- ✅ `registry_batch_no`: Resets per registry

---

## SQL Update Script - All Fields

### Step 1: Add Helper Columns (to stage the calculations)

```sql
-- Add temporary columns to calculate new values
ALTER TABLE grouping ADD 
    new_number INT NULL,
    new_group INT NULL,
    new_sys_batch_no INT NULL,
    new_registry_batch_no INT NULL;
```

### Step 2: Calculate All New Values Using CTE

```sql
WITH AllCalculations AS (
    SELECT 
        id,
        -- GLOBAL COUNTERS: position in entire table
        ROW_NUMBER() OVER (ORDER BY id) AS global_position,
        
        -- PER-REGISTRY COUNTER: position within each registry
        ROW_NUMBER() OVER (PARTITION BY registry ORDER BY id) AS position_in_registry,
        
        registry
    FROM grouping
)
UPDATE grouping
SET 
    new_number = ac.global_position,
    new_group = ((ac.global_position - 1) / 100) + 1,
    new_sys_batch_no = ((ac.global_position - 1) / 100) + 1,
    new_registry_batch_no = ((ac.position_in_registry - 1) / 100) + 1
FROM grouping g
INNER JOIN AllCalculations ac ON g.id = ac.id;
```

### Step 3: Verify Calculations (Before Committing)

```sql
-- Check first 20 records
SELECT TOP 20
    id,
    awaiting_fileno,
    registry,
    number AS old_number,
    new_number,
    grouping AS old_group,
    new_group,
    sys_batch_no AS old_sys_batch_no,
    new_sys_batch_no,
    registry_batch_no AS old_registry_batch_no,
    new_registry_batch_no
FROM grouping
ORDER BY id;
```

**Expected Output:**
```
id | awaiting_fileno | registry     | old_number | new_number | old_group | new_group | old_sys_batch_no | new_sys_batch_no | old_registry_batch_no | new_registry_batch_no
---|-----------------|--------------|------------|-----------|-----------|-----------|------------------|-----------------|-----|-----
1  | RES-1981-1      | Registry 1   | 1          | 1         | 1         | 1         | 1                | 1               | 1   | 1
2  | RES-1981-2      | Registry 1   | 2          | 2         | 1         | 1         | 1                | 1               | 1   | 1
...
100| ?               | Registry 1   | 100        | 100       | 1         | 1         | 1                | 1               | 1   | 1
101| ?               | Registry 1   | 101        | 101       | 2         | 2         | 2                | 2               | 2   | 2
```

### Step 4: Check Registry Boundaries - RESET Points

```sql
-- Check around Registry 1 → Registry 2 boundary
SELECT TOP 5
    id,
    awaiting_fileno,
    registry,
    new_number,
    new_group,
    new_sys_batch_no,
    new_registry_batch_no
FROM grouping
WHERE id BETWEEN 879998 AND 880002
ORDER BY id;
```

**Expected Output:**
```
id      | awaiting_fileno | registry    | new_number | new_group | new_sys_batch_no | new_registry_batch_no
--------|-----------------|-------------|-----------|-----------|------------------|---------------------
879998  | ?               | Registry 1  | 879998    | 8800      | 8800             | 8800
879999  | ?               | Registry 1  | 879999    | 8800      | 8800             | 8800
880000  | ?               | Registry 1  | 880000    | 8800      | 8800             | 8800
880001  | MUN-1981-?      | Registry 2  | 880001    | 8801      | 8801             | 1        ← RESET!
880002  | MUN-1981-?      | Registry 2  | 880002    | 8801      | 8801             | 1        ← RESET!
```

```sql
-- Check around Registry 2 → Registry 3 boundary
SELECT TOP 5
    id,
    awaiting_fileno,
    registry,
    new_number,
    new_group,
    new_sys_batch_no,
    new_registry_batch_no
FROM grouping
WHERE id BETWEEN 3599998 AND 3600002
ORDER BY id;
```

**Expected Output:**
```
id      | awaiting_fileno | registry    | new_number | new_group | new_sys_batch_no | new_registry_batch_no
--------|-----------------|-------------|-----------|-----------|------------------|---------------------
3599998 | ?               | Registry 2  | 3599998   | 35999     | 35999            | 27200
3599999 | ?               | Registry 2  | 3599999   | 35999     | 35999            | 27200
3600000 | ?               | Registry 2  | 3600000   | 36000     | 36000            | 27200
3600001 | ?               | Registry 3  | 3600001   | 36001     | 36001            | 1        ← RESET!
3600002 | ?               | Registry 3  | 3600002   | 36001     | 36001            | 1        ← RESET!
```

### Step 5: Compare Old vs New Values - Count Differences

```sql
-- Count how many records have changed per field
SELECT 
    'number' AS field,
    COUNT(*) AS records_changed
FROM grouping
WHERE number <> new_number

UNION ALL

SELECT 
    'group' AS field,
    COUNT(*) AS records_changed
FROM grouping
WHERE grouping <> new_group

UNION ALL

SELECT 
    'sys_batch_no' AS field,
    COUNT(*) AS records_changed
FROM grouping
WHERE sys_batch_no <> new_sys_batch_no

UNION ALL

SELECT 
    'registry_batch_no' AS field,
    COUNT(*) AS records_changed
FROM grouping
WHERE registry_batch_no <> new_registry_batch_no;
```

**Expected Output:**
```
field               | records_changed
--------------------|---------------
number              | 1,800,001  (almost all)
group               | 1,800,001  (almost all)
sys_batch_no        | 1,800,001  (almost all)
registry_batch_no   | 1,800,001  (almost all)
```

### Step 6: Apply the Update (Point of No Return)

**⚠️ BACKUP FIRST! ⚠️**

```sql
-- Make sure you have a backup before this!
BACKUP DATABASE [your_database_name] TO DISK = 'C:\Backup\grouping_before_update.bak';
```

```sql
-- Commit the changes
UPDATE grouping
SET 
    number = new_number,
    grouping = new_group,
    sys_batch_no = new_sys_batch_no,
    registry_batch_no = new_registry_batch_no
WHERE new_number IS NOT NULL;
```

### Step 7: Clean Up Helper Columns

```sql
-- Remove temporary columns
ALTER TABLE grouping DROP COLUMN new_number, new_group, new_sys_batch_no, new_registry_batch_no;
```

### Step 8: Final Validation

```sql
-- Verify final results match expected values
SELECT 
    COUNT(*) AS total_records,
    MIN(number) AS min_number,
    MAX(number) AS max_number,
    MIN(grouping) AS min_group,
    MAX(grouping) AS max_group,
    MIN(sys_batch_no) AS min_sys_batch_no,
    MAX(sys_batch_no) AS max_sys_batch_no,
    MIN(registry_batch_no) AS min_registry_batch_no,
    MAX(registry_batch_no) AS max_registry_batch_no
FROM grouping;
```

**Expected Output:**
```
total_records | min_number | max_number | min_group | max_group | min_sys_batch_no | max_sys_batch_no | min_registry_batch_no | max_registry_batch_no
--------------|------------|-----------|-----------|-----------|------------------|------------------|-----------------------|---------------------
7,200,001     | 1          | 7200000   | 1         | 72000     | 1                | 72000            | 1                     | 36000
```

---

## Detailed Before & After Examples

### Registry 1 - First Records
```
BEFORE:
id=1, RES-1981-1: number=1, group=1, sys_batch_no=1, registry_batch_no=1

AFTER:
id=1, RES-1981-1: number=1, group=1, sys_batch_no=1, registry_batch_no=1
(No change - already correct)
```

### Registry 1 - Middle Records
```
BEFORE:
id=440001, RES-RC-1981-1: number=440001, group=4401, sys_batch_no=4401, registry_batch_no=4401

AFTER:
id=440001, RES-RC-1981-1: number=440001, group=4401, sys_batch_no=4401, registry_batch_no=4401
(No change - already correct)
```

### Registry 1 - Last Records
```
BEFORE:
id=880000, ?, registry=Registry 1: number=880000, group=8800, sys_batch_no=8800, registry_batch_no=8800

AFTER:
id=880000, ?, registry=Registry 1: number=880000, group=8800, sys_batch_no=8800, registry_batch_no=8800
(No change - already correct)
```

### Registry 2 - First Records (RESET POINT)
```
BEFORE:
id=880001, MUN-1981-1: number=880001, group=8801, sys_batch_no=8801, registry_batch_no=8801 ✗ WRONG

AFTER:
id=880001, MUN-1981-1: number=880001, group=8801, sys_batch_no=8801, registry_batch_no=1 ✓ FIXED!
                                                                      (reset per registry)
```

### Registry 2 - Last Records
```
BEFORE:
id=3600000, ?, registry=Registry 2: number=3600000, group=36000, sys_batch_no=36000, registry_batch_no=36000 ✗ WRONG

AFTER:
id=3600000, ?, registry=Registry 2: number=3600000, group=36000, sys_batch_no=36000, registry_batch_no=27200 ✓ FIXED!
```

### Registry 3 - First Records (RESET POINT)
```
BEFORE:
id=3600001, ?: number=3600001, group=36001, sys_batch_no=36001, registry_batch_no=36001 ✗ WRONG

AFTER:
id=3600001, ?: number=3600001, group=36001, sys_batch_no=36001, registry_batch_no=1 ✓ FIXED!
                                                                 (reset per registry)
```

### Registry 3 - Last Record
```
BEFORE:
id=7200000, (last record): number=7200000, group=72000, sys_batch_no=72000, registry_batch_no=36000

AFTER:
id=7200000, (last record): number=7200000, group=72000, sys_batch_no=72000, registry_batch_no=36000
(No change - already correct)
```

---

## Update Plan Checklist

| Step | Action | Time | Status |
|------|--------|------|--------|
| 1 | Add helper columns | 1 min | ⏳ |
| 2 | Calculate all values in helper columns | 3 min | ⏳ |
| 3 | Verify calculations (first 20 records) | 1 min | ⏳ |
| 4 | Check Registry boundaries (reset points) | 2 min | ⏳ |
| 5 | Count differences per field | 1 min | ⏳ |
| 6 | **BACKUP DATABASE** | 5 min | ⏳ |
| 7 | Apply UPDATE to actual columns | 3 min | ⏳ |
| 8 | Clean up helper columns | 1 min | ⏳ |
| 9 | Final validation (min/max values) | 1 min | ⏳ |

**Total Time:** ~18 minutes

---

## Key Changes Summary

| Field | OLD | NEW | Change |
|-------|-----|-----|--------|
| `number` | Mixed/wrong logic | 1 → 7,200,000 (pure global) | ~All records |
| `group` | May be wrong | 1 → 72,000 (pure global) | ~All records |
| `sys_batch_no` | May be wrong | 1 → 72,000 (pure global, same as group) | ~All records |
| `registry_batch_no` | Doesn't reset per registry | Resets: 1→8.8K, 1→27.2K, 1→36K | ~1.8M records |

---

## Ready to Execute?

✅ **I am ready to:**
1. Run the full SQL update script
2. Create before/after comparison report
3. Generate validation queries
4. Execute and verify all changes

**What would you like me to do?**
- Execute the complete update?
- Test on a subset first (e.g., first 100K records)?
- Create a rollback plan first?
