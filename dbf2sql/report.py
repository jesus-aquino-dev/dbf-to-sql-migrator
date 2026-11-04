"""Excel report of a migration: summary, schema mapping and data issues."""
from __future__ import annotations

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
TOTAL_FONT = Font(bold=True)
MAX_WIDTH = 60


def write_report(results, path):
    wb = Workbook()

    summary_rows = [
        [r.name, r.source.name, r.migrated, r.deleted, len(r.issues), round(r.seconds, 2)]
        for r in results
    ]
    summary = wb.active
    summary.title = "Summary"
    _fill(summary,
          ["Table", "Source file", "Rows migrated", "Deleted rows skipped", "Data issues", "Seconds"],
          summary_rows)
    summary.append([
        "TOTAL", "",
        sum(r.migrated for r in results),
        sum(r.deleted for r in results),
        sum(len(r.issues) for r in results),
        round(sum(r.seconds for r in results), 2),
    ])
    for cell in summary[summary.max_row]:
        cell.font = TOTAL_FONT

    _fill(wb.create_sheet("Schema"),
          ["Table", "Field", "DBF type", "SQL type"],
          [[r.name, *column] for r in results for column in r.schema])

    _fill(wb.create_sheet("Issues"),
          ["Table", "Row", "Key", "Field", "Raw value", "Problem"],
          [[i.table, i.row, i.key, i.field, i.value, i.problem]
           for r in results for i in r.issues])

    wb.save(path)


def _fill(ws, headers, rows):
    ws.append(headers)
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions
    for col, header in enumerate(headers, start=1):
        width = max(len(str(value)) for value in [header, *(row[col - 1] for row in rows)])
        ws.column_dimensions[get_column_letter(col)].width = min(width + 2, MAX_WIDTH)
