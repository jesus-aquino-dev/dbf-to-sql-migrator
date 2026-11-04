"""Create SQL tables and load DBF records into them."""
from __future__ import annotations

from sqlalchemy import Column, MetaData, Table, inspect

from .typemap import sql_type

BATCH_SIZE = 1000


class TableExistsError(RuntimeError):
    pass


def existing_tables(engine, names):
    inspector = inspect(engine)
    return [name for name in names if inspector.has_table(name)]


def load_table(engine, source, replace=False):
    """Create the table for `source` and insert its records in one transaction.

    Returns the number of rows inserted. If anything fails, nothing is kept.
    """
    table = Table(
        source.name, MetaData(),
        *(Column(field.name, sql_type(field)) for field in source.fields),
    )
    with engine.begin() as conn:
        if replace:
            table.drop(conn, checkfirst=True)
        elif inspect(conn).has_table(source.name):
            raise TableExistsError(f"table '{source.name}' already exists (use --replace)")
        table.create(conn)

        inserted = 0
        batch = []
        for record in source.records():
            batch.append(record)
            if len(batch) >= BATCH_SIZE:
                conn.execute(table.insert(), batch)
                inserted += len(batch)
                batch = []
        if batch:
            conn.execute(table.insert(), batch)
            inserted += len(batch)
    return inserted
