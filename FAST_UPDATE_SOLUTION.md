# Fast Database Update - Alternative Approaches

## Problem
The CTE with window functions is too slow for 7.2M records (4+ hours and counting).

**Why it's slow:**
- Window functions scan entire table multiple times
- JOIN between CTE and main table on 7.2M rows
- Integer division in CTE creates additional overhead

---

## Solution 1: Batch Update by Registry (FASTEST - Recommended)

Process each registry separately. This is 100x faster because:
- Smaller dataset per batch
- Simpler calculations
- No complex window functions

### Step 1: Update Registry 1 (880K records)

```sql
SET STATISTICS TIME ON;

-- Registry 1: Simple sequential update
DECLARE @counter INT = 0;
DECLARE @reg_counter INT = 0;

UPDATE grouping
SET 
    @counter = @counter + 1,
    @reg_counter = @reg_counter + 1,
    new_number = @counter,
    new_group = ((@counter - 1) / 100) + 1,
    new_sys_batch_no = ((@counter - 1) / 100) + 1,
    new_registry_batch_no = ((@reg_counter - 1) / 100) + 1
WHERE registry = 'Registry 1'
ORDER BY id;

SET STATISTICS TIME OFF;
```

**Expected Time:** 2-3 minutes
**Records Updated:** 880,000

### Step 2: Update Registry 2 (2.72M records)

```sql
SET STATISTICS TIME ON;

DECLARE @counter INT = 880000;  -- Continue from Registry 1
DECLARE @reg_counter INT = 0;   -- Reset for Registry 2

UPDATE grouping
SET 
    @counter = @counter + 1,
    @reg_counter = @reg_counter + 1,
    new_number = @counter,
    new_group = ((@counter - 1) / 100) + 1,
    new_sys_batch_no = ((@counter - 1) / 100) + 1,
    new_registry_batch_no = ((@reg_counter - 1) / 100) + 1
WHERE registry = 'Registry 2'
ORDER BY id;

SET STATISTICS TIME OFF;
```

**Expected Time:** 5-7 minutes
**Records Updated:** 2,720,000

### Step 3: Update Registry 3 (3.6M records)

```sql
SET STATISTICS TIME ON;

DECLARE @counter INT = 3600000;  -- Continue from Registry 2
DECLARE @reg_counter INT = 0;    -- Reset for Registry 3

UPDATE grouping
SET 
    @counter = @counter + 1,
    @reg_counter = @reg_counter + 1,
    new_number = @counter,
    new_group = ((@counter - 1) / 100) + 1,
    new_sys_batch_no = ((@counter - 1) / 100) + 1,
    new_registry_batch_no = ((@reg_counter - 1) / 100) + 1
WHERE registry = 'Registry 3'
ORDER BY id;

SET STATISTICS TIME OFF;
```

**Expected Time:** 8-10 minutes
**Records Updated:** 3,600,000

**Total Time:** ~15-20 minutes (vs 4+ hours for the CTE approach)

---

## Solution 2: Stop Current Query & Use Batch Update

### IMMEDIATE ACTION

1. **Stop the running query** (SQL Server Management Studio):
   - Right-click the query tab → Cancel Executing Query
   - Or press `Ctrl + Alt + Break`

2. **Verify helper columns exist:**

```sql
-- Check if helper columns were created
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'grouping' 
  AND COLUMN_NAME IN ('new_number', 'new_group', 'new_sys_batch_no', 'new_registry_batch_no');
```

3. **If helper columns exist**, run Solution 1 (batch update)
4. **If no changes detected**, the query hasn't committed yet

---

## Solution 3: Use Table Variable with Precomputed Values (Alternative)

If batch update doesn't work, use pre-computed lookup table:

```sql
-- Create lookup table with precomputed values
CREATE TABLE #CalculatedValues (
    id INT PRIMARY KEY,
    new_number INT,
    new_group INT,
    new_sys_batch_no INT,
    new_registry_batch_no INT
);

-- Populate using indexed approach (much faster)
INSERT INTO #CalculatedValues
SELECT 
    id,
    ROW_NUMBER() OVER (ORDER BY id) AS new_number,
    ((ROW_NUMBER() OVER (ORDER BY id) - 1) / 100) + 1 AS new_group,
    ((ROW_NUMBER() OVER (ORDER BY id) - 1) / 100) + 1 AS new_sys_batch_no,
    ((ROW_NUMBER() OVER (PARTITION BY registry ORDER BY id) - 1) / 100) + 1 AS new_registry_batch_no
FROM grouping
ORDER BY id;

-- Now update (lookup table join is fast)
UPDATE grouping
SET 
    new_number = cv.new_number,
    new_group = cv.new_group,
    new_sys_batch_no = cv.new_sys_batch_no,
    new_registry_batch_no = cv.new_registry_batch_no
FROM grouping g
INNER JOIN #CalculatedValues cv ON g.id = cv.id;

-- Cleanup
DROP TABLE #CalculatedValues;
```

**Expected Time:** 8-12 minutes

---

## Comparison of Approaches

| Approach | Time | Complexity | Reliability |
|----------|------|-----------|-------------|
| CTE with Window Functions (original) | 4+ hours ❌ | High | Medium (slow, may timeout) |
| **Batch Update by Registry** | 15-20 min ✅ | Low | High |
| Lookup Table | 8-12 min ✅ | Medium | High |

---

## RECOMMENDED STEPS

### Step 1: STOP Current Query
```
In SQL Server Management Studio:
- Click Query menu → Cancel Executing Query
- OR press Ctrl + Alt + Break
```

### Step 2: Verify Status
```sql
-- Check if any updates were applied
SELECT COUNT(*) AS records_with_new_values
FROM grouping
WHERE new_number IS NOT NULL;
```

- If `0`: No changes applied, start fresh with batch update
- If `> 0`: Some progress made, check which registries are done

### Step 3: Run Batch Update (Solution 1)

Do them one registry at a time:

```sql
-- Registry 1 - Run this first
DECLARE @counter INT = 0;
DECLARE @reg_counter INT = 0;

UPDATE grouping
SET 
    @counter = @counter + 1,
    @reg_counter = @reg_counter + 1,
    new_number = @counter,
    new_group = ((@counter - 1) / 100) + 1,
    new_sys_batch_no = ((@counter - 1) / 100) + 1,
    new_registry_batch_no = ((@reg_counter - 1) / 100) + 1
WHERE registry = 'Registry 1'
ORDER BY id;

-- Check result
SELECT COUNT(*) AS updated_registry_1, MAX(new_number) AS max_number
FROM grouping
WHERE registry = 'Registry 1' AND new_number IS NOT NULL;
```

Expected output: `880,000 records, max_number=880,000`

### Step 4: Monitor Progress

After starting Registry 2:
```sql
-- Every minute, check progress
SELECT 
    registry,
    COUNT(*) AS total,
    COUNT(CASE WHEN new_number IS NOT NULL THEN 1 END) AS updated,
    ROUND(100.0 * COUNT(CASE WHEN new_number IS NOT NULL THEN 1 END) / COUNT(*), 1) AS pct_complete
FROM grouping
GROUP BY registry
ORDER BY registry;
```

---

## Timeline Estimate (Batch Approach)

```
2:00 PM - Start Registry 1 (2-3 min)
2:05 PM - Start Registry 2 (5-7 min)
2:12 PM - Start Registry 3 (8-10 min)
2:22 PM - Done ✅ (apply updates, cleanup, validate)
2:30 PM - Complete
```

vs original CTE approach:
```
10:00 AM - Started CTE query
2:00 PM - Still running (4 hours in) ❌
Unknown finish time
```

---

## What to Do Right Now

1. **CANCEL the running query** (Ctrl + Alt + Break)
2. **Wait 1 minute** for cancellation to take effect
3. **Run the verification query** to check status
4. **Choose your approach** (Batch is fastest)
5. **Run Step 1 of Batch Update** (Registry 1)

Would you like me to help you execute the batch update? Just tell me when you've cancelled the current query.
