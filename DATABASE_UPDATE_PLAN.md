# Database Update Plan - Correct registry_batch_no for All Records

## Objective
Update the `grouping` table starting from the first record (id=1) to calculate correct `registry_batch_no` values based on the fixed logic: **reset per registry**.

---

## Current Database State

```sql
SELECT TOP 10 id, awaiting_fileno, number, grouping, sys_batch_no, registry_batch_no 
FROM grouping 
ORDER BY id;
```

**Problem:** `registry_batch_no` doesn't reset when transitioning between registries.

---

## Step 1: Understand Registry Boundaries

From the code configuration:

```
Registry 1: RES, COM, IND, AG, RES-RC
  Categories: 5
  Years: 1981-1991 (11 years)
  Numbers per year: 10,000
  Total: 5 × 11 × 10,000 = 550,000 records
  
  Wait, let me recalculate...
  Actually 8 categories × 11 years × 10,000 = 880,000 records

Registry 2: MUN, etc
  Categories: 8  
  Years: 1981-2014 (34 years)
  Total: 8 × 34 × 10,000 = 2,720,000 records

Registry 3: (remaining categories)
  Total: 7,200,000 - 880,000 - 2,720,000 = 3,600,000 records
```

**Registry Boundaries:**
- Registry 1: Records 1 → 880,000
- Registry 2: Records 880,001 → 3,600,000
- Registry 3: Records 3,600,001 → 7,200,000

---

## Step 2: Calculate Correct registry_batch_no

**Formula:** `registry_batch_no = (position_in_registry / 100) + 1`

Where `position_in_registry` is the record's position within its registry.

**Examples:**

```
Registry 1:
  Record 1-100     → registry_batch_no = 1
  Record 101-200   → registry_batch_no = 2
  Record 880,000   → registry_batch_no = 8,800

Registry 2:
  Record 880,001   → registry_batch_no = 1 (RESET!)
  Record 880,100   → registry_batch_no = 1
  Record 880,101   → registry_batch_no = 2 (NEW BATCH)
  Record 3,600,000 → registry_batch_no = 27,200

Registry 3:
  Record 3,600,001 → registry_batch_no = 1 (RESET!)
  Record 7,200,000 → registry_batch_no = 36,000
```

---

## Step 3: SQL Script to Update All Records

### Option A: Using Window Functions (Recommended - Faster)

```sql
-- Get registry boundaries from actual data
DECLARE @reg1_end INT;
DECLARE @reg2_end INT;

-- Find the max ID where registry = 'Registry 1'
SELECT @reg1_end = MAX(id) FROM grouping WHERE registry = 'Registry 1';
SELECT @reg2_end = MAX(id) FROM grouping WHERE registry = 'Registry 2';

-- Reset registry_batch_no for all records based on position within registry
UPDATE grouping
SET registry_batch_no = CASE 
    WHEN registry = 'Registry 1' 
        THEN ((ROW_NUMBER() OVER (PARTITION BY registry ORDER BY id) - 1) / 100) + 1
    WHEN registry = 'Registry 2' 
        THEN ((ROW_NUMBER() OVER (PARTITION BY registry ORDER BY id) - 1) / 100) + 1
    WHEN registry = 'Registry 3' 
        THEN ((ROW_NUMBER() OVER (PARTITION BY registry ORDER BY id) - 1) / 100) + 1
END
WHERE id >= 1;
```

### Option B: Using CTE (Clearer Logic)

```sql
-- CTE to calculate position per registry
WITH RegistryPositions AS (
    SELECT 
        id,
        awaiting_fileno,
        registry,
        ROW_NUMBER() OVER (PARTITION BY registry ORDER BY id) AS position_in_registry
    FROM grouping
)
UPDATE grouping
SET registry_batch_no = ((rp.position_in_registry - 1) / 100) + 1
FROM grouping g
INNER JOIN RegistryPositions rp ON g.id = rp.id;
```

---

## Step 4: Validation - Verify the Update

### Check Registry 1
```sql
SELECT TOP 10 
    id, 
    awaiting_fileno, 
    registry,
    registry_batch_no,
    -- Calculate what it should be:
    ((ROW_NUMBER() OVER (ORDER BY id) - 1) / 100) + 1 AS should_be
FROM grouping 
WHERE registry = 'Registry 1'
ORDER BY id;
```

**Expected Output:**
```
id      | awaiting_fileno | registry    | registry_batch_no | should_be
--------|-----------------|-------------|-------------------|----------
1       | RES-1981-1      | Registry 1  | 1                 | 1
2       | RES-1981-2      | Registry 1  | 1                 | 1
...
100     | ?               | Registry 1  | 1                 | 1
101     | ?               | Registry 1  | 2                 | 2
...
880000  | RES-RC-1981-?   | Registry 1  | 8800              | 8800
```

### Check Registry 2 - RESET Point
```sql
SELECT TOP 10 
    id, 
    awaiting_fileno, 
    registry,
    registry_batch_no,
    -- Position within Registry 2:
    ((ROW_NUMBER() OVER (PARTITION BY registry ORDER BY id) - 1) / 100) + 1 AS should_be
FROM grouping 
WHERE registry = 'Registry 2'
ORDER BY id;
```

**Expected Output:**
```
id      | awaiting_fileno | registry    | registry_batch_no | should_be
--------|-----------------|-------------|-------------------|----------
880001  | MUN-1981-1      | Registry 2  | 1                 | 1  ← RESET!
880002  | MUN-1981-2      | Registry 2  | 1                 | 1
...
880100  | ?               | Registry 2  | 1                 | 1
880101  | ?               | Registry 2  | 2                 | 2
...
3600000 | (last of Reg 2) | Registry 2  | 27200             | 27200
```

### Check Registry 3 - RESET Point
```sql
SELECT TOP 10 
    id, 
    awaiting_fileno, 
    registry,
    registry_batch_no
FROM grouping 
WHERE registry = 'Registry 3'
ORDER BY id;
```

**Expected Output:**
```
id      | awaiting_fileno | registry    | registry_batch_no
--------|-----------------|-------------|-------------------
3600001 | (first of Reg3) | Registry 3  | 1                 ← RESET!
3600002 | (2nd of Reg 3)  | Registry 3  | 1
...
3600100 | ?               | Registry 3  | 1
3600101 | ?               | Registry 3  | 2
...
7200000 | (last record)   | Registry 3  | 36000
```

---

## Step 5: Before & After Comparison

### BEFORE (Wrong)
```
Record 880,000 (last of Registry 1): registry_batch_no = 8,800  ✓
Record 880,001 (first of Registry 2): registry_batch_no = 8,801  ✗ WRONG! Should be 1

Record 3,600,000 (last of Registry 2): registry_batch_no = 36,000 ✗ (might be 27,200 or 36,000)
Record 3,600,001 (first of Registry 3): registry_batch_no = 36,001 ✗ WRONG! Should be 1
```

### AFTER (Correct)
```
Record 880,000 (last of Registry 1): registry_batch_no = 8,800   ✓
Record 880,001 (first of Registry 2): registry_batch_no = 1      ✓ RESET!

Record 3,600,000 (last of Registry 2): registry_batch_no = 27,200 ✓
Record 3,600,001 (first of Registry 3): registry_batch_no = 1     ✓ RESET!

Record 7,200,000 (last record): registry_batch_no = 36,000      ✓
```

---

## Step 6: Update Plan Summary

| Step | Action | SQL/Code | Time Est |
|------|--------|----------|----------|
| 1 | Backup database | `BACKUP DATABASE grouping TO DISK = 'backup.bak'` | 5 min |
| 2 | Update all records | Option B (CTE approach) | 2 min |
| 3 | Validate Registry 1 | Check 10 samples | 1 min |
| 4 | Validate Registry 2 (reset point) | Check around id=880,001 | 1 min |
| 5 | Validate Registry 3 (reset point) | Check around id=3,600,001 | 1 min |
| 6 | Count mismatches | Query to compare before/after logic | 2 min |
| 7 | Commit changes | Or rollback if validation fails | 1 min |

**Total Time:** ~12 minutes

---

## Key Changes in Table

**Column: `registry_batch_no`**

| Records | Registry | New Values | Pattern |
|---------|----------|-----------|---------|
| 1 - 880,000 | Registry 1 | 1 - 8,800 | Continuous |
| 880,001 - 3,600,000 | Registry 2 | 1 - 27,200 | **RESETS to 1** |
| 3,600,001 - 7,200,000 | Registry 3 | 1 - 36,000 | **RESETS to 1** |

**Unchanged Columns:**
- `number`: Still 1 - 7,200,000 (global)
- `group`: Still 1 - 72,000 (global)
- `sys_batch_no`: Still 1 - 72,000 (global)

---

## Ready to Execute?

Would you like me to:
1. ✅ **Run the SQL UPDATE script** against your database?
2. 📋 **Create a detailed validation report** first?
3. 🔄 **Test on a subset** of records first (e.g., first 10,000)?

Let me know!
