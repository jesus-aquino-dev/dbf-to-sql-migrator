"""Migrate every DBF table in a folder."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine

from .reader import DbfSource, Issue
from .target import TableExistsError, existing_tables, load_table


@dataclass
class TableResult:
    name: str
    source: Path
    migrated: int
    deleted: int
    seconds: float
    schema: list[tuple[str, str, str]]
    issues: list[Issue] = field(default_factory=list)


def find_dbf_files(folder, only=None):
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() == ".dbf")
    if only:
        wanted = {name.lower() for name in only}
        files = [p for p in files if p.stem.lower() in wanted]
    return files


def migrate_folder(folder, db_url, encoding=None, replace=False, only=None, progress=None):
    """Migrate the .dbf files in `folder` to the database at `db_url`.

    Checks for existing tables before touching anything, so a run without
    `replace` either migrates everything or nothing.
    """
    files = find_dbf_files(folder, only)
    if not files:
        raise FileNotFoundError(f"no .dbf files found in {folder}")

    engine = create_engine(db_url)
    try:
        if not replace:
            clashes = existing_tables(engine, [p.stem.lower() for p in files])
            if clashes:
                raise TableExistsError(
                    f"tables already exist: {', '.join(clashes)} (use --replace)"
                )

        results = []
        for path in files:
            if progress:
                progress(f"migrating {path.name} ...")
            start = time.perf_counter()
            source = DbfSource(path, encoding)
            migrated = load_table(engine, source, replace=replace)
            results.append(TableResult(
                name=source.name,
                source=path,
                migrated=migrated,
                deleted=source.deleted_count,
                seconds=time.perf_counter() - start,
                schema=source.schema(),
                issues=source.issues,
            ))
        return results
    finally:
        engine.dispose()
