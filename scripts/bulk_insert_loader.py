#!/usr/bin/env python3
"""CSV bulk loader that leverages SQL Server BULK INSERT for fileNumber imports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from database_connection import DatabaseConnection

BULK_INSERT_SQL = """
DECLARE @control_tag NVARCHAR(100) = ?;
DECLARE @now DATETIME2(3) = SYSDATETIME();
DECLARE @inserted INT = 0;
DECLARE @matched INT = 0;

CREATE TABLE #FileImport (
    SN NVARCHAR(50) NULL,
    mlsfNo NVARCHAR(255) NULL,
    kangisFileNo NVARCHAR(255) NULL,
    plotNo NVARCHAR(255) NULL,
    tpPlanNo NVARCHAR(255) NULL,
    currentAllottee NVARCHAR(255) NULL,
    layoutName NVARCHAR(255) NULL,
    districtName NVARCHAR(255) NULL,
    lgaName NVARCHAR(255) NULL
);

BULK INSERT #FileImport
FROM '{csv_path}'
WITH (
    FORMAT='CSV',
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK,
    CODEPAGE='65001',
    KEEPNULLS
);

SELECT
    LTRIM(RTRIM(f.mlsfNo)) AS mlsfNo,
    LTRIM(RTRIM(f.kangisFileNo)) AS kangisFileNo,
    LTRIM(RTRIM(f.plotNo)) AS plotNo,
    LTRIM(RTRIM(f.tpPlanNo)) AS tpPlanNo,
    LTRIM(RTRIM(f.currentAllottee)) AS currentAllottee,
    LTRIM(RTRIM(f.layoutName)) AS layoutName,
    LTRIM(RTRIM(f.districtName)) AS districtName,
    LTRIM(RTRIM(f.lgaName)) AS lgaName,
    LTRIM(RTRIM(
        REPLACE(REPLACE(REPLACE(UPPER(ISNULL(f.mlsfNo,'')), 'AND EXTENSION', ''), '(TEMP)', ''), '  ', ' ')
    )) AS cleaned_mlsf
INTO #Prepared
FROM #FileImport f
WHERE ISNULL(LTRIM(RTRIM(f.mlsfNo)), '') <> '';

DROP TABLE #FileImport;

;WITH matched AS (
    SELECT
        p.*,
        g.tracking_id
    FROM #Prepared p
    LEFT JOIN grouping g ON LTRIM(RTRIM(UPPER(g.awaiting_fileno))) = p.cleaned_mlsf
)
INSERT INTO dbo.fileNumber (
    kangisFileNo,
    mlsfNo,
    NewKANGISFileNo,
    FileName,
    created_at,
    location,
    created_by,
    type,
    is_deleted,
    SOURCE,
    plot_no,
    tp_no,
    tracking_id,
    date_migrated,
    migrated_by,
    migration_source,
    test_control
)
SELECT
    NULLIF(m.kangisFileNo, ''),
    m.mlsfNo,
    NULL,
    NULLIF(m.currentAllottee, ''),
    @now,
    CASE
        WHEN NULLIF(m.layoutName, '') IS NOT NULL THEN CONCAT(m.layoutName, ', ', m.lgaName, ', ', m.districtName)
        ELSE CONCAT(m.lgaName, ', ', m.districtName)
    END,
    'CSV Bulk Loader',
    'KANGIS',
    0,
    'KANGIS GIS',
    NULLIF(m.plotNo, ''),
    NULLIF(m.tpPlanNo, ''),
    m.tracking_id,
    CONVERT(NVARCHAR(30), @now, 126),
    '1',
    'KANGIS GIS',
    @control_tag
FROM matched m;

SET @inserted = @@ROWCOUNT;

WITH grouping_matches AS (
    SELECT DISTINCT
        g.id,
        p.mlsfNo
    FROM #Prepared p
    JOIN grouping g ON LTRIM(RTRIM(UPPER(g.awaiting_fileno))) = p.cleaned_mlsf
)
UPDATE g
SET mapping = 1,
    mls_fileno = gm.mlsfNo,
    test_control = @control_tag
FROM grouping g
JOIN grouping_matches gm ON g.id = gm.id;

SET @matched = (SELECT COUNT(*) FROM grouping_matches);

SELECT
    (SELECT COUNT(*) FROM #Prepared) AS prepared_records,
    @inserted AS inserted_records,
    @matched AS matched_grouping,
    (SELECT COUNT(*) FROM #Prepared) - @matched AS unmatched_grouping;

DROP TABLE #Prepared;
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load CSV data into SQL Server using BULK INSERT"
    )
    parser.add_argument(
        "--csv",
        default="FileNos_PRO.csv",
        help="Path to the CSV file on the local filesystem"
    )
    parser.add_argument(
        "--server-path",
        help="Path to the CSV as seen by SQL Server (if different from --csv)"
    )
    parser.add_argument(
        "--control-tag",
        required=True,
        help="Value stored in test_control for tracking/cleanup"
    )
    return parser.parse_args()


def validate_paths(csv_path: Path) -> None:
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)


def run_bulk_insert(csv_server_path: str, control_tag: str) -> None:
    db = DatabaseConnection()
    conn = db.get_connection()
    if conn is None:
        print("Database connection failed. Check .env settings.", file=sys.stderr)
        sys.exit(1)

    sql = BULK_INSERT_SQL.format(csv_path=csv_server_path.replace("'", "''"))

    try:
        cursor = conn.cursor()
        cursor.execute(sql, control_tag)
        summary_rows = None
        while True:
            if cursor.description:
                data = cursor.fetchall()
                if data:
                    summary_rows = data
            if not cursor.nextset():
                break
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Bulk insert failed: {exc}") from exc
    finally:
        if 'cursor' in locals():
            cursor.close()
        conn.close()

    if summary_rows:
        row = summary_rows[0]
        print("Bulk insert completed")
        print(f"Prepared records : {row.prepared_records}")
        print(f"Inserted records : {row.inserted_records}")
        print(f"Matched grouping  : {row.matched_grouping}")
        print(f"Unmatched grouping: {row.unmatched_grouping}")


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv).expanduser().resolve()
    validate_paths(csv_path)
    server_path = args.server_path or str(csv_path)
    print(dedent(
        f"""
        Running BULK INSERT loader...
          CSV (local) : {csv_path}
          CSV (server): {server_path}
          Control tag : {args.control_tag}
        """
    ).strip())
    run_bulk_insert(server_path, args.control_tag)


if __name__ == "__main__":
    main()
