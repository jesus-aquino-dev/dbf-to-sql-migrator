import sqlite3
from collections import namedtuple
from contextlib import closing

import pytest
from openpyxl import load_workbook
from sqlalchemy import BigInteger, Boolean, Date, Integer, Numeric, String, Text

from dbf2sql.migrate import migrate_folder
from dbf2sql.report import write_report
from dbf2sql.target import TableExistsError
from dbf2sql.typemap import describe, sql_type
from generate_demo_data import generate

Field = namedtuple("Field", "name type length decimal_count")


@pytest.mark.parametrize("field, expected", [
    (Field("nombre", "C", 40, 0), String),
    (Field("codigo", "N", 6, 0), Integer),
    (Field("total", "N", 14, 0), BigInteger),
    (Field("precio", "N", 12, 2), Numeric),
    (Field("fecha", "D", 8, 0), Date),
    (Field("activo", "L", 1, 0), Boolean),
    (Field("obs", "M", 10, 0), Text),
])
def test_type_mapping(field, expected):
    assert isinstance(sql_type(field), expected)


def test_describe_uses_foxpro_notation():
    assert describe(Field("nombre", "C", 40, 0)) == "C(40)"
    assert describe(Field("precio", "N", 12, 2)) == "N(12,2)"
    assert describe(Field("fecha", "D", 8, 0)) == "D"


@pytest.fixture
def demo_dir(tmp_path):
    folder = tmp_path / "demo"
    generate(folder)
    return folder


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "migrated.db"


def run(demo_dir, db_path, **kwargs):
    results = migrate_folder(demo_dir, f"sqlite:///{db_path}", **kwargs)
    return {r.name: r for r in results}


def query(db_path, sql):
    with closing(sqlite3.connect(db_path)) as conn:
        return conn.execute(sql).fetchall()


def test_migrates_every_active_record(demo_dir, db_path):
    results = run(demo_dir, db_path)

    assert set(results) == {"clientes", "productos", "ventas"}
    for name, result in results.items():
        assert query(db_path, f"select count(*) from {name}") == [(result.migrated,)]
    assert results["clientes"].migrated == 120
    assert results["productos"].migrated == 24
    assert results["ventas"].migrated == 1498
    assert results["ventas"].deleted == 2


def test_text_is_decoded_and_trimmed(demo_dir, db_path):
    run(demo_dir, db_path)

    names = {row[0] for row in query(db_path, "select nombre from clientes")}
    assert "Peña Núñez, María José" in names
    assert "gonzález benítez, carlos" in names


def test_bad_values_become_null_and_are_reported(demo_dir, db_path):
    results = run(demo_dir, db_path)

    clientes = results["clientes"].issues
    assert [i.problem for i in clientes] == ["invalid date"] * 3
    assert {i.value for i in clientes} == {"20230231", "20221345", "19/05/19"}
    # three invalid dates plus one that was empty to begin with
    assert query(db_path, "select count(*) from clientes where fec_alta is null") == [(4,)]

    productos = sorted(i.problem for i in results["productos"].issues)
    assert productos == ["invalid number", "invalid number", "numeric overflow (****)"]
    assert results["ventas"].issues == []


def test_issue_points_to_the_record_key(demo_dir, db_path):
    results = run(demo_dir, db_path)

    issue = next(i for i in results["clientes"].issues if i.value == "20230231")
    assert (issue.row, issue.key, issue.field) == (15, "15", "fec_alta")


def test_existing_tables_are_kept_unless_replace(demo_dir, db_path):
    run(demo_dir, db_path)

    with pytest.raises(TableExistsError):
        run(demo_dir, db_path)

    results = run(demo_dir, db_path, replace=True)
    assert query(db_path, "select count(*) from ventas") == [(results["ventas"].migrated,)]


def test_only_selected_tables(demo_dir, db_path):
    results = run(demo_dir, db_path, only=["Clientes"])
    assert list(results) == ["clientes"]


def test_report_has_summary_schema_and_issues(demo_dir, db_path, tmp_path):
    results = run(demo_dir, db_path)
    report = tmp_path / "report.xlsx"
    write_report(list(results.values()), report)

    wb = load_workbook(report)
    assert wb.sheetnames == ["Summary", "Schema", "Issues"]
    total_issues = sum(len(r.issues) for r in results.values())
    assert wb["Issues"].max_row == 1 + total_issues
    assert wb["Summary"].cell(row=wb["Summary"].max_row, column=1).value == "TOTAL"
