# dbf2sql: Visual FoxPro → SQL migrator

Move data out of **Visual FoxPro / dBase tables (`.dbf`)** into a modern SQL database (**PostgreSQL, SQL Server, MySQL or SQLite**) without losing records to the dirty data that legacy systems collect over the years, and get an **Excel report** of exactly what happened.

> 🇪🇸 **Resumen en español:** herramienta en Python que migra tablas `.dbf` de Visual FoxPro a una base SQL. No se detiene ante datos inválidos (fechas imposibles, números con letras, desbordes `****`): los guarda como NULL y los lista en un reporte Excel para corregirlos. Todos los datos de ejemplo son ficticios.

## Why

Many businesses still run on Visual FoxPro. When they move to the web, the hard part is the data: years of hand-typed values that a strict import rejects. A single `31/02` date can make a whole table fail.

`dbf2sql` migrates **every readable record**, turns unreadable values into `NULL`, and lists each one so it can be fixed at the source.

## Features

- Migrates every `.dbf` in a folder, or only the tables you pick
- Maps FoxPro types to SQL types: `C(40)` → `VARCHAR(40)`, `N(12,2)` → `NUMERIC(12,2)`, `D` → `DATE`, `L` → `BOOLEAN`…
- Handles code pages (`cp1252`, `cp850`…) so accents and `ñ` arrive intact
- Tolerates bad data: invalid dates, letters in numbers, `****` overflow
- Skips deleted records (`DELETE` without `PACK`) and counts them
- One transaction per table: a table is migrated completely or not at all
- Never overwrites existing tables unless you ask with `--replace`
- Excel report with three sheets: **Summary**, **Schema** (type mapping) and **Issues** (every bad value, with its record key)

## Quick start

```bash
pip install -r requirements.txt

# 1. Create fictional FoxPro tables with typical legacy problems
python scripts/generate_demo_data.py demo_data

# 2. Migrate them (SQLite by default, no setup needed)
python -m dbf2sql demo_data
```

Output:

![Migration run in the terminal](docs/screenshots/terminal_migration.png)

## The Excel report

**Summary**: what was migrated, table by table.

![Summary sheet of the Excel report](docs/screenshots/report_summary.png)

**Issues**: every value that could not be read, with the record key so it can be fixed in FoxPro.

![Issues sheet of the Excel report](docs/screenshots/report_issues.png)

<details>
<summary><b>Schema</b>: how each FoxPro field was mapped to SQL</summary>

![Schema sheet of the Excel report](docs/screenshots/report_schema.png)

</details>

## Migrating to PostgreSQL (or any other database)

Any [SQLAlchemy database URL](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls) works. Keep the password out of your command history by using the `DBF2SQL_DB` environment variable:

```bash
pip install psycopg2-binary
export DBF2SQL_DB="postgresql+psycopg2://user:password@localhost:5432/mydb"
python -m dbf2sql path/to/foxpro/data --encoding cp1252
```

## Options

| Option | Description |
|---|---|
| `source` | Folder with the `.dbf` files |
| `--db URL` | Target database. Default: `$DBF2SQL_DB` or `sqlite:///output/migrated.db` |
| `--report PATH` | Excel report path. Default: `output/migration_report.xlsx` |
| `--encoding CP` | Code page of the DBF text (`cp1252`, `cp850`…). Default: read from the file header |
| `--tables NAME …` | Migrate only these tables |
| `--replace` | Drop and recreate tables that already exist |

## Type mapping

| FoxPro | SQL |
|---|---|
| `C(n)` Character | `VARCHAR(n)` |
| `N(n,0)` Numeric, no decimals | `INTEGER`, or `BIGINT` above 9 digits |
| `N(n,d)` Numeric | `NUMERIC(n,d)` |
| `F` Float, `B` Double | `FLOAT` |
| `I` Integer | `INTEGER` |
| `Y` Currency | `NUMERIC(19,4)` |
| `D` Date | `DATE` |
| `T` DateTime | `TIMESTAMP` |
| `L` Logical | `BOOLEAN` |
| `M` Memo, `G` General | `TEXT` |

## Project structure

```
dbf2sql/
  reader.py    # reads .dbf files, tolerating bad values
  typemap.py   # FoxPro → SQL type mapping
  target.py    # creates tables and inserts in batches
  migrate.py   # orchestrates a whole folder
  report.py    # Excel report
  cli.py       # command line interface
scripts/
  generate_demo_data.py   # fictional demo tables
tests/
```

## Tests

```bash
python -m pytest
```

![Test run](docs/screenshots/tests.png)

## License

MIT. All demo data (names, tax ids, phone numbers) is fictional.
