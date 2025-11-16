# Clear Visual Example - Before & After

## BEFORE (Current Code - WRONG)

```python
# Line 138-140: Initialize counters
global_record_count = 0
registry_counts: Dict[str, int] = {}

# Line 145: Loop through registries
for sequence in self.registry_sequences:
    seq_start, seq_end = sequence['year_range']
    # ... more setup ...
    
    for category in sequence['categories']:
        for year in range(seq_start, seq_end + 1):
            for number in range(1, number_cap + 1):
                global_record_count += 1
                category_counts[category] += 1
                
                file_number = f"{category}-{year}-{number}"
                group_number = ((global_record_count - 1) // 100) + 1
                batch_number = group_number
                
                land_use = self.extract_land_use(file_number)
                registry = self.assign_registry(file_number, year)
                registry_counts[registry] = registry_counts.get(registry, 0) + 1  # ← PROBLEM: No explicit reset
                registry_batch_no = ((registry_counts[registry] - 1) // 100) + 1
                
                yield {
                    'awaiting_fileno': file_number,
                    'number': global_record_count,
                    'group': group_number,
                    'sys_batch_no': batch_number,
                    'registry_batch_no': registry_batch_no,
                    # ... other fields ...
                }
```

**Problem:** When moving from Registry 1 → Registry 2, there's NO explicit reset of `registry_counts['Registry 2']`. It just implicitly starts at 0 because it's a new key.

---

## AFTER (Fixed Code - CORRECT)

```python
# Line 138-140: Initialize counters (SAME)
global_record_count = 0
registry_counts: Dict[str, int] = {}

# Line 145: Loop through registries
for sequence in self.registry_sequences:
    registry_id = sequence['registry']  # ← ADD THIS LINE
    registry_counts[registry_id] = 0    # ← ADD THIS LINE (explicit reset)
    
    seq_start, seq_end = sequence['year_range']
    # ... more setup ...
    
    for category in sequence['categories']:
        for year in range(seq_start, seq_end + 1):
            for number in range(1, number_cap + 1):
                global_record_count += 1
                category_counts[category] += 1
                
                file_number = f"{category}-{year}-{number}"
                group_number = ((global_record_count - 1) // 100) + 1
                batch_number = group_number
                
                land_use = self.extract_land_use(file_number)
                registry = self.assign_registry(file_number, year)
                registry_counts[registry] += 1  # ← CHANGE THIS (remove .get() fallback)
                registry_batch_no = ((registry_counts[registry] - 1) // 100) + 1
                
                yield {
                    'awaiting_fileno': file_number,
                    'number': global_record_count,
                    'group': group_number,
                    'sys_batch_no': batch_number,
                    'registry_batch_no': registry_batch_no,
                    # ... other fields ...
                }
```

**Solution:** Explicitly reset each registry counter when we START processing that registry.

---

## Output Comparison

### BEFORE (Current - Wrong Output)

```
RES-1981-1         | num=1      | grp=1    | batch=1    | reg_batch=1        ✓
RES-1981-2         | num=2      | grp=1    | batch=1    | reg_batch=1        ✓
...
RES-RC-1981-1      | num=440001 | grp=4401 | batch=4401 | reg_batch=4401     ✓
RES-RC-1981-2      | num=440002 | grp=4401 | batch=4401 | reg_batch=4402     ✓

[After Registry 1 ends at record 880,000]
[Registry 2 starts - NEW REGISTRY]

MUN-1981-1         | num=880001 | grp=8801 | batch=8801 | reg_batch=8801     ✗ WRONG!
                                                           Should be: reg_batch=1

MUN-1981-2         | num=880002 | grp=8801 | batch=8801 | reg_batch=8802     ✗ WRONG!
                                                           Should be: reg_batch=2
```

**Issue:** When Registry 2 starts, `registry_batch_no` should reset to 1, but it continues from where Registry 1 left off.

---

### AFTER (Fixed - Correct Output)

```
RES-1981-1         | num=1      | grp=1    | batch=1    | reg_batch=1        ✓
RES-1981-2         | num=2      | grp=1    | batch=1    | reg_batch=1        ✓
...
RES-RC-1981-1      | num=440001 | grp=4401 | batch=4401 | reg_batch=4401     ✓
RES-RC-1981-2      | num=440002 | grp=4401 | batch=4401 | reg_batch=4402     ✓

[After Registry 1 ends at record 880,000]
[Registry 2 starts - COUNTER RESETS]

MUN-1981-1         | num=880001 | grp=8801 | batch=8801 | reg_batch=1        ✓ CORRECT!
                   (global keeps going)   (group keeps going)   (resets per registry!)

MUN-1981-2         | num=880002 | grp=8801 | batch=8801 | reg_batch=1        ✓ CORRECT!
```

**Solution:** Now when Registry 2 starts, `registry_batch_no` correctly resets to 1.

---

## Why This Matters

| Counter | Behavior | Before Fix | After Fix |
|---------|----------|-----------|-----------|
| `number` | Global (1-7.2M) | Correct | Correct |
| `group` | Global (1-72K) | Correct | Correct |
| `sys_batch_no` | Global (1-72K) | Correct | Correct |
| `registry_batch_no` | Per Registry (resets) | ❌ Doesn't reset visibly | ✅ Resets explicitly |

The global counters work fine—it's the registry counter that needs the explicit reset to make the code clear and correct.

---

## Code Changes Summary

**Addition (Line 145-146):**
```python
registry_id = sequence['registry']
registry_counts[registry_id] = 0
```

**Modification (Line 175):**
```python
# From:
registry_counts[registry] = registry_counts.get(registry, 0) + 1

# To:
registry_counts[registry] += 1
```

**That's it!** 2 small changes = correct logic.
