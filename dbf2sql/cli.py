"""Command line interface: python -m dbf2sql SOURCE_DIR [options]."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

from .migrate import migrate_folder
from .report import write_report
from .target import TableExistsError

DEFAULT_DB = "sqlite:///output/migrated.db"
DEFAULT_REPORT = Path("output/migration_report.xlsx")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dbf2sql",
        description="Migrate Visual FoxPro / dBase tables (.dbf) to a SQL database "
                    "and get an Excel report of the result.",
    )
    parser.add_argument("source", type=Path, help="folder with the .dbf files")
    parser.add_argument(
        "--db",
        default=os.environ.get("DBF2SQL_DB", DEFAULT_DB),
        help=f"SQLAlchemy database URL. Defaults to the DBF2SQL_DB environment "
             f"variable, or {DEFAULT_DB}",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT,
                        help=f"Excel report path (default: {DEFAULT_REPORT})")
    parser.add_argument("--encoding",
                        help="code page of the text in the DBF files, e.g. cp1252 or cp850 "
                             "(default: taken from the file header)")
    parser.add_argument("--tables", nargs="+", metavar="NAME",
                        help="migrate only these tables")
    parser.add_argument("--replace", action="store_true",
                        help="drop and recreate tables that already exist")
    return parser


def _ensure_sqlite_folder(db_url):
    url = make_url(db_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)


def main(argv=None):
    args = build_parser().parse_args(argv)
    _ensure_sqlite_folder(args.db)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    try:
        results = migrate_folder(args.source, args.db, encoding=args.encoding,
                                 replace=args.replace, only=args.tables, progress=print)
    except (FileNotFoundError, TableExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_report(results, args.report)

    print()
    print(f"{'table':<16}{'rows':>8}{'deleted':>10}{'issues':>9}")
    for r in results:
        print(f"{r.name:<16}{r.migrated:>8}{r.deleted:>10}{len(r.issues):>9}")
    print(f"\nreport: {args.report}")
    return 0
