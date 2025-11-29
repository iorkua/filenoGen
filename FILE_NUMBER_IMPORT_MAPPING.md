# File Number Import Mapping

## Column Roles and Mappings

| CSV Column       | Role in Import                             | Target Field(s)                           | Transform / Notes                                                                 |
|------------------|---------------------------------------------|-------------------------------------------|-----------------------------------------------------------------------------------|
| `mlsfNo`         | Primary identifier for dedupe and matching  | `dbo.fileNumber.mlsfNo`; grouping `mls_fileno` | Cleaned (remove `AND EXTENSION`, `(TEMP)`, extra spaces) for lookup against `dbo.grouping.awaiting_fileno`; original value inserted. |
| `kangisFileNo`   | Existing KANGIS reference                   | `dbo.fileNumber.kangisFileNo`             | Trimmed; blank values stored as `NULL`.                                            |
| `currentAllottee`| Allottee name                               | `dbo.fileNumber.FileName`                 | Trimmed; blank values stored as `NULL`.                                            |
| `layoutName`     | Location context (part 1)                   | `dbo.fileNumber.location`                 | Combined with LGA and district (`"<layout>, <lga>, <district>"`); layout omitted when empty. |
| `districtName`   | Location context (part 2)                   | `dbo.fileNumber.location`                 | See `layoutName`.                                                                 |
| `lgaName`        | Location context (part 3)                   | `dbo.fileNumber.location`                 | See `layoutName`.                                                                 |
| `plotNo`         | Plot identifier                             | `dbo.fileNumber.plot_no`                  | Trimmed; blank values stored as `NULL`.                                            |
| `tpPlanNo`       | TP / plan reference                         | `dbo.fileNumber.tp_no`                    | Trimmed; blank values stored as `NULL`.                                            |

## Derived and Constant Fields

Set in `src/fast_csv_importer.py` for each inserted record:

- `NewKANGISFileNo` → `NULL`.
- `created_at` and `date_migrated` → current import timestamp.
- `created_by` → `CSV Bulk Importer`.
- `type` → `KANGIS`.
- `is_deleted` → `0`.
- `SOURCE` and `migration_source` → `KANGIS GIS`.
- `migrated_by` → `'1'`.
- `tracking_id` → populated when the cleaned `mlsfNo` matches a record in `dbo.grouping`; otherwise `NULL`.
- `test_control` → control tag passed with the import  

## Grouping Table Side Effects

For each cleaned `mlsfNo` that matches `dbo.grouping.awaiting_fileno`:

- `mapping` is updated to `1`.
- `mls_fileno` is set to the original `mlsfNo` value.
- `test_control` is copied from the import control tag.

Rows without a grouping match leave `mapping` unchanged and keep `tracking_id = NULL`.