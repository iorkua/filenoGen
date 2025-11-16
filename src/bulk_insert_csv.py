"""Execute a SQL Server BULK INSERT for a CSV file using the shared database config."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from textwrap import dedent
from typing import List

from database_connection import DatabaseConnection


DEFAULT_TABLE = "[dbo].[fileNumber]"
DEFAULT_FIELD_TERM = ","
DEFAULT_ROW_TERM = "\n"


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def escape_path(value: str) -> str:
    return value.replace("'", "''")


def build_bulk_insert_sql(
    table: str,
    csv_path: str,
    first_row: int,
    field_terminator: str,
    row_terminator: str,
    codepage: str | None,
    tablock: bool,
    keep_identity: bool,
    batch_size: int | None,
) -> str:
    options: List[str] = [f"FIRSTROW = {first_row}", f"FIELDTERMINATOR = '{field_terminator}'", f"ROWTERMINATOR = '{row_terminator}'"]
    if codepage:
        options.append(f"CODEPAGE = '{codepage}'")
    if tablock:
        options.append("TABLOCK")
    if keep_identity:
        options.append("KEEPIDENTITY")
    if batch_size:
        options.append(f"BATCHSIZE = {batch_size}")

    options.append("FORMAT='CSV'")

    options_sql = ",\n    ".join(options)
    escaped_path = escape_path(csv_path)
    return dedent(
        f"""
        BULK INSERT {table}
        FROM '{escaped_path}'
        WITH (
            {options_sql}
        );
        """
    ).strip()


def run_bulk_insert(args: argparse.Namespace) -> None:
    configure_logging(args.verbose)
    csv_path = args.csv
    if not args.assume_exists:
        path_obj = Path(csv_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"CSV file not found on local machine: {csv_path}. Use --assume-exists if only the server can see it.")

    sql = build_bulk_insert_sql(
        table=args.table,
        csv_path=csv_path,
        first_row=args.first_row,
        field_terminator=args.field_terminator,
        row_terminator=args.row_terminator,
        codepage=args.codepage,
        tablock=args.tablock,
        keep_identity=args.keep_identity,
        batch_size=args.batch_size,
    )

    logging.info("Connecting to SQL Server ...")
    db = DatabaseConnection()
    conn = db.get_connection('pyodbc')
    if not conn:
        raise RuntimeError("Failed to open database connection")

    cursor = None
    try:
        logging.info("Running BULK INSERT into %s", args.table)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        logging.info("BULK INSERT completed successfully")
    finally:
        if cursor:
            cursor.close()
        conn.close()


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SQL Server BULK INSERT for a CSV file")
    parser.add_argument("--csv", required=True, help="Path to CSV file (as seen by SQL Server)")
    parser.add_argument("--table", default=DEFAULT_TABLE, help="Target table (default: %(default)s)")
    parser.add_argument("--first-row", type=int, default=2, help="BULK INSERT FIRSTROW (default: %(default)s)")
    parser.add_argument("--field-terminator", default=DEFAULT_FIELD_TERM, help="FIELDTERMINATOR (default: '%(default)s')")
    parser.add_argument("--row-terminator", default=DEFAULT_ROW_TERM, help=r"ROWTERMINATOR (default: newline)")
    parser.add_argument("--codepage", default="65001", help="CODEPAGE (default: UTF-8 65001)")
    parser.add_argument("--tablock", action="store_true", help="Use TABLOCK for faster, minimally logged loads")
    parser.add_argument("--keep-identity", action="store_true", help="Preserve identity values during load")
    parser.add_argument("--batch-size", type=int, default=None, help="Optional BULK INSERT batch size")
    parser.add_argument("--assume-exists", action="store_true", help="Skip client-side CSV existence check")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)
    run_bulk_insert(args)


if __name__ == "__main__":
    main()
