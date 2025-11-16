# File Number Generator - Numbering Fix Plan

## 🔴 Current Problem

The code is mixing **two different numbering systems**:

```python
# CURRENT CODE (WRONG):
global_record_count = 0              # Global counter across ALL registries

for sequence in self.registry_sequences:
    for category in sequence['categories']:
        for year in range(seq_start, seq_end + 1):
            for number in range(1, number_cap + 1):
                global_record_count += 1            # ← Incrementing globally
                
                group_number = ((global_record_count - 1) // 100) + 1
                registry_batch_no = ((registry_counts[registry] - 1) // 100) + 1
                
                yield {
                    'number': global_record_count,      # ← WRONG: Should be per-category
                    'group': group_number,              # ← WRONG: Should be per-category
                    'sys_batch_no': batch_number,       # ← WRONG: Should be per-category
                    'registry_batch_no': registry_batch_no  # ✓ Correct (per-registry)
                }
```

**But the database shows:**
- `number`: 1 (per-category counter)
- `group`: 1 (per-category groups)
- `sys_batch_no`: 1 (per-category batches)
- `registry_batch_no`: 1 (per-registry batches)

---

## ✅ What The Numbering SHOULD Be

Based on your database structure and actual data:

```
RES-RC-1981-1:
├─ number: 1                    (1st record in RES-RC category across all years)
├─ group: 1                     (Records 1-100 of RES-RC = Group 1)
├─ sys_batch_no: 1              (Records 1-100 of RES-RC = Batch 1)
└─ registry_batch_no: 4,401     (4,401st batch in Registry 1 overall)

RES-RC-1981-101:
├─ number: 101                  (101st record in RES-RC category)
├─ group: 2                     (Records 101-200 of RES-RC = Group 2)
├─ sys_batch_no: 2              (Records 101-200 of RES-RC = Batch 2)
└─ registry_batch_no: 4,402     (4,402nd batch in Registry 1 overall)
```

**Key Rules:**
1. **`number`** = Per-category sequential counter (1 to 450,000 for each category)
2. **`group`** = Per-category group numbering (100 records per group)
3. **`sys_batch_no`** = Per-category batch numbering (100 records per batch, same as group)
4. **`registry_batch_no`** = Global per-registry counter (continuous across all categories in registry)

---

## 🛠️ The Fix

### Change Required in `src/file_number_generator.py`

**Current (Lines 155-165):**
```python
category_counts: Dict[str, int] = {}
# Global counters for group and batch numbering
global_record_count = 0
registry_counts: Dict[str, int] = {}

for sequence in self.registry_sequences:
    # ... categories loop ...
    
    for category in sequence['categories']:
        category_counts.setdefault(category, 0)
        generated_before = category_counts[category]
```

**Fixed (Lines 155-165):**
```python
category_counts: Dict[str, int] = {}
category_record_counts: Dict[str, int] = {}  # ← ADD: Per-category record counter
registry_counts: Dict[str, int] = {}

for sequence in self.registry_sequences:
    # ... categories loop ...
    
    for category in sequence['categories']:
        category_counts.setdefault(category, 0)
        category_record_counts.setdefault(category, 0)  # ← ADD: Initialize per-category
        generated_before = category_counts[category]
```

**Current (Lines 168-192):**
```python
for number in range(1, number_cap + 1):
    global_record_count += 1
    category_counts[category] += 1

    file_number = f"{category}-{year}-{number}"
    group_number = ((global_record_count - 1) // self.records_per_group) + 1
    batch_number = group_number

    land_use = self.extract_land_use(file_number)
    registry = self.assign_registry(file_number, year)
    registry_counts[registry] = registry_counts.get(registry, 0) + 1
    registry_batch_no = ((registry_counts[registry] - 1) // self.records_per_group) + 1
    tracking_id = self.generate_tracking_id()

    yield {
        'awaiting_fileno': file_number,
        'created_by': 'Generated',
        'number': global_record_count,      # ← WRONG
        'year': year,
        'landuse': land_use,
        'created_at': datetime.now(),
        'registry': registry,
        'mls_fileno': None,
        'mapping': 0,
        'group': group_number,               # ← WRONG
        'sys_batch_no': batch_number,        # ← WRONG
        'registry_batch_no': registry_batch_no,
        'tracking_id': tracking_id
    }
```

**Fixed (Lines 168-192):**
```python
for number in range(1, number_cap + 1):
    category_counts[category] += 1
    category_record_counts[category] += 1  # ← ADD: Increment per-category counter

    file_number = f"{category}-{year}-{number}"
    
    # Group and batch based on CATEGORY counter, not global
    group_number = ((category_record_counts[category] - 1) // self.records_per_group) + 1
    batch_number = group_number

    land_use = self.extract_land_use(file_number)
    registry = self.assign_registry(file_number, year)
    registry_counts[registry] = registry_counts.get(registry, 0) + 1
    registry_batch_no = ((registry_counts[registry] - 1) // self.records_per_group) + 1
    tracking_id = self.generate_tracking_id()

    yield {
        'awaiting_fileno': file_number,
        'created_by': 'Generated',
        'number': category_record_counts[category],  # ← FIX: Per-category counter
        'year': year,
        'landuse': land_use,
        'created_at': datetime.now(),
        'registry': registry,
        'mls_fileno': None,
        'mapping': 0,
        'group': group_number,                        # ← FIX: Per-category groups
        'sys_batch_no': batch_number,                 # ← FIX: Per-category batches
        'registry_batch_no': registry_batch_no,       # ✓ Keep (already correct)
        'tracking_id': tracking_id
    }
```

---

## 📊 Summary of Changes

| Field | Current Logic | Fixed Logic | Impact |
|-------|---|---|---|
| **number** | Global (1→7.2M) | Per-category (1→450K) | CORRECTS to match DB |
| **group** | Global groups | Per-category groups | CORRECTS to match DB |
| **sys_batch_no** | Same as global group | Same as per-category group | CORRECTS to match DB |
| **registry_batch_no** | Per-registry counter | Per-registry counter | ✓ Already correct |

---

## ⚡ How Fast Can We Fix This?

### Option 1: **Code Fix Only** (Fast - 5 minutes)
- **Time:** ~5 minutes to code and test
- **Action:** Update `src/file_number_generator.py` with the 3 changes above
- **Impact:** Future generations will be correct
- **Problem:** Existing 1.8M+ records in DB remain incorrect

### Option 2: **Code Fix + DB Correction** (Moderate - 1-2 hours)
- **Time:** ~1-2 hours total
- **Steps:**
  1. Fix the code (5 min)
  2. Generate corrected data with fixed code (15-30 min for 1000 test records)
  3. Write SQL script to recalculate all fields for existing 1.8M+ records (15 min)
  4. Execute SQL update (15-30 min depending on DB load)
  5. Validate results (15 min)

### Option 3: **Full Regeneration** (Slow - 2-3 hours)
- **Time:** ~2-3 hours total
- **Steps:**
  1. Fix the code (5 min)
  2. Backup current data (5 min)
  3. Clear grouping table (2 min)
  4. Regenerate all 7.2M records with fixed code (40 min)
  5. Create indexes (15 min)
  6. Validate (15 min)

---

## 🎯 Recommended Approach: **Option 2** (Best Balance)

**Why:** Fixes future generations AND corrects existing data without full regeneration

**SQL Script to Fix Existing Records:**

```sql
-- 1. Add temporary column if needed to store category
-- (Optional, can calculate from awaiting_fileno)

-- 2. Recalculate per-category record number
-- This assumes records are ordered by category → year → number
WITH cte_numbered AS (
    SELECT 
        id,
        awaiting_fileno,
        ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(awaiting_fileno, 1, CHARINDEX('-', awaiting_fileno) - 1)
            ORDER BY id
        ) as new_number,
        
        -- Calculate group (100 per group)
        (ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(awaiting_fileno, 1, CHARINDEX('-', awaiting_fileno) - 1)
            ORDER BY id
        ) - 1) / 100 + 1 as new_group,
        
        -- Calculate sys_batch_no (same as group)
        (ROW_NUMBER() OVER (
            PARTITION BY SUBSTRING(awaiting_fileno, 1, CHARINDEX('-', awaiting_fileno) - 1)
            ORDER BY id
        ) - 1) / 100 + 1 as new_sys_batch_no
)
UPDATE grouping
SET 
    [number] = cte.new_number,
    [group] = cte.new_group,
    [sys_batch_no] = cte.new_sys_batch_no
FROM grouping g
JOIN cte_numbered cte ON g.id = cte.id;

-- 3. Verify results
SELECT TOP 10 awaiting_fileno, [number], [group], sys_batch_no, registry_batch_no
FROM grouping
WHERE awaiting_fileno LIKE 'RES-RC%'
ORDER BY id;
```

---

## 📋 Execution Plan

### Step 1: Code Fix (5 min)
✅ Update `src/file_number_generator.py`:
- Add `category_record_counts` dictionary
- Change `number` to use `category_record_counts[category]`
- Change `group_number` calculation to use category counter

### Step 2: Test (10 min)
✅ Generate sample (100 records):
```python
from src.file_number_generator import FileNumberGenerator
gen = FileNumberGenerator()
samples = gen.generate_sample_data(records_per_category=10)
for s in samples[-10:]:
    print(f"{s['awaiting_fileno']}: num={s['number']}, grp={s['group']}, batch={s['sys_batch_no']}, reg_batch={s['registry_batch_no']}")
```

### Step 3: Database Update (30 min)
✅ Run SQL correction script
✅ Validate against known records (RES-RC-1981-1 should have number=1, group=1, etc.)

### Step 4: Verify (15 min)
✅ Check row counts
✅ Check distribution
✅ Check for null/invalid values

---

## ⏱️ Total Time Estimate

| Task | Time |
|------|------|
| Code fix | 5 min |
| Testing | 10 min |
| SQL update execution | 30 min |
| Validation | 15 min |
| **TOTAL** | **~60 minutes** |

---

## 🚀 Ready to Execute?

Would you like me to:
1. **Just fix the code** (5 min) → Future generations correct
2. **Fix code + test** (15 min) → Verify fix works
3. **Full Option 2** (60 min) → Everything corrected

Let me know which approach you prefer!
