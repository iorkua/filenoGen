"""Tests for duplicate handling in the fast CSV importer."""

from typing import List, Tuple

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fast_csv_importer import FastCSVImporter  # noqa: E402


class _StubCursor:
    """Minimal cursor stub that returns predefined rows."""

    def __init__(self, rows: List[Tuple[str]]):
        self._rows = rows

    def execute(self, query, params):  # pylint: disable=unused-argument
        return None

    def fetchall(self):
        return self._rows

    def close(self):
        return None


class _StubConnection:
    """Connection stub that hands out stub cursors."""

    def __init__(self, rows: List[Tuple[str]]):
        self._rows = rows

    def cursor(self):
        return _StubCursor(self._rows)

    def close(self):
        return None


class _StubDatabase:
    """Database stub matching the DatabaseConnection interface."""

    def __init__(self, rows: List[Tuple[str]]):
        self._rows = rows

    def get_connection(self, *_args, **_kwargs):  # pylint: disable=unused-argument
        return _StubConnection(self._rows)


def test_prepare_records_skips_existing_and_csv_duplicates():
    importer = FastCSVImporter()
    importer.prefetch_grouping_lookup = lambda _values: None  # type: ignore[assignment]
    importer.lookup_tracking_id = lambda _cleaned: None  # type: ignore[assignment]

    importer.db_connection = _StubDatabase(rows=[('MLS-001',)])  # type: ignore[assignment]

    records = [
        {'mlsfNo': 'MLS-001', 'layoutName': '', 'lgaName': 'LGA', 'districtName': 'District'},
        {'mlsfNo': 'MLS-002', 'layoutName': '', 'lgaName': 'LGA', 'districtName': 'District'},
        {'mlsfNo': 'MLS-002 ', 'layoutName': '', 'lgaName': 'LGA', 'districtName': 'District'},
    ]

    prepared = importer.prepare_records(records)

    assert importer.duplicate_records == 2
    assert len(prepared) == 1
    assert prepared[0]['mlsfNo'] == 'MLS-002'
