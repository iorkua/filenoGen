"""Utility to convert the FileNos Excel workbook into a CSV ready for BULK INSERT."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from typing import List

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
DEFAULT_EXCEL = BASE_DIR / "FileNos_PRO.xlsx"
DEFAULT_CSV = BASE_DIR / "exports" / "FileNos_PRO.csv"


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def sanitize_columns(columns: List[str]) -> List[str]:
    return [col.strip().replace(" ", "_") for col in columns]


def export_excel_to_csv(excel_path: Path, csv_path: Path, sheet_name: str | int | None = None) -> None:
    logging.info("Reading Excel file: %s", excel_path)
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    logging.info("Loaded %d rows with columns %s", len(df), list(df.columns))

    logging.info("Cleaning column names for CSV output")
    df.columns = sanitize_columns(df.columns)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Writing CSV to %s", csv_path)
    df.to_csv(csv_path, index=False, encoding="utf-8", lineterminator="\n")
    logging.info("CSV export completed")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert FileNos Excel workbook to CSV for bulk loading")
    parser.add_argument("--excel", type=Path, default=DEFAULT_EXCEL, help="Path to the source Excel file")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Target CSV output path")
    parser.add_argument("--sheet", default=None, help="Excel sheet name or index (default: first sheet)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    configure_logging(args.verbose)
    export_excel_to_csv(args.excel, args.csv, args.sheet)


if __name__ == "__main__":
    main()
