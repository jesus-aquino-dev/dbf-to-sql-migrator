"""Read DBF tables without letting one bad value abort the whole migration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dbfread import DBF, FieldParser

from .typemap import describe, sql_type

# _NullFlags: internal Visual FoxPro field, not user data.
SKIPPED_TYPES = {"0"}


@dataclass
class Issue:
    table: str
    row: int
    key: str
    field: str
    value: str
    problem: str


def _tolerant_parser(sink):
    """Build a dbfread parser that turns unreadable values into NULL.

    Each problem is appended to `sink` as (field name, raw bytes, problem) so
    the caller can tie it to the record being read.
    """

    class TolerantParser(FieldParser):
        def parseD(self, field, data):
            return self._safe(super().parseD, field, data, "invalid date")

        def parseT(self, field, data):
            return self._safe(super().parseT, field, data, "invalid datetime")

        def parseN(self, field, data):
            if data.strip().startswith(b"*"):
                sink.append((field.name, data, "numeric overflow (****)"))
                return None
            return self._safe(super().parseN, field, data, "invalid number")

        def parseF(self, field, data):
            return self.parseN(field, data)

        def _safe(self, parse, field, data, problem):
            try:
                return parse(field, data)
            except ValueError:
                sink.append((field.name, data, problem))
                return None

    return TolerantParser


def _clean(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class DbfSource:
    """One DBF table: its fields, its records and the problems found reading them."""

    def __init__(self, path, encoding=None):
        self.path = Path(path)
        self.name = self.path.stem.lower()
        self.issues: list[Issue] = []
        self._pending = []
        self.table = DBF(
            str(self.path),
            encoding=encoding,
            char_decode_errors="replace",
            lowernames=True,
            parserclass=_tolerant_parser(self._pending),
        )
        self.fields = [f for f in self.table.fields if f.type not in SKIPPED_TYPES]

    @property
    def deleted_count(self):
        return len(self.table.deleted)

    def schema(self):
        return [(f.name, describe(f), str(sql_type(f))) for f in self.fields]

    def records(self):
        """Yield each active (non-deleted) record as a dict of clean values."""
        names = [f.name for f in self.fields]
        for row, record in enumerate(self.table, start=1):
            values = {name: _clean(record[name]) for name in names}
            if self._pending:
                key = str(values[names[0]])
                for field, raw, problem in self._pending:
                    raw_text = raw.decode(self.table.encoding, "replace").strip()
                    self.issues.append(Issue(self.name, row, key, field, raw_text, problem))
                self._pending.clear()
            yield values
