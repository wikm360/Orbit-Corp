"""Turn the "PVF" sheet of the company-wide EVM workbook into a small file the volume report reads directly.

    python scripts/extract_pv_plan.py "Total EVM Rep-MGSH SHAHRIVAR V4.xls" [-o "برنامه PV آبان.xlsx"]

Output: one sheet, title "برنامه PV پروژه‌ها در ماه <ماه>", header ردیف / نام پروژه / PV ماهانه (ریال), one row per project.
Upload it in the report wizard as «برنامه‌ی PV ماهانه»; the week's PV is its share by days (see .agents/flows/volume-report.md)."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Font  # noqa: E402

from app.features.volume_report.extraction.pv_plan import detect_pv_plan  # noqa: E402
from app.features.volume_report.jalali import MONTHS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", help="the workbook (.xls/.xlsx) that has the PV plan sheet")
    parser.add_argument("-o", "--output", help="output .xlsx (default: next to the source)")
    args = parser.parse_args()
    plan = detect_pv_plan(args.source)
    if plan is None:
        print("No PV plan sheet found (a visible sheet with «نام پروژه» and a PV column, no CPI/SPI).", file=sys.stderr)
        return 1
    month = MONTHS[plan.month - 1] if plan.month else "؟"
    wb = Workbook()
    ws = wb.active
    ws.title = "PV"
    ws.sheet_view.rightToLeft = True
    ws.append([f"برنامه PV پروژه‌ها در ماه {month}"])
    ws.append([f"منبع: {Path(args.source).name} · شیت {plan.sheet_name.strip()}"])
    ws.append(["ردیف", "نام پروژه", "PV ماهانه (ریال)"])
    for cell in ws[3]:
        cell.font = Font(bold=True)
    ws["A1"].font = Font(bold=True, size=13)
    for index, row in enumerate(plan.rows, start=1):
        ws.append([index, row.project_name, float(row.pv_month)])
    ws.append(["", "جمع", float(sum(r.pv_month for r in plan.rows))])
    ws.column_dimensions["B"].width = 70
    ws.column_dimensions["C"].width = 24
    for row in ws.iter_rows(min_row=4, min_col=3, max_col=3):
        for cell in row:
            cell.number_format = "#,##0"
            cell.alignment = Alignment(horizontal="left")
    out = Path(args.output) if args.output else Path(args.source).with_name(f"برنامه PV {month}.xlsx")
    wb.save(out)
    print(f"{len(plan.rows)} projects -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
