"""File-level extraction: probe every sheet, parse the income ones, build the `sheet_log` stored on `vr_report_files`."""

import os
from dataclasses import dataclass, field
from typing import Any

from app.features.volume_report.extraction.continuation import continuation_grid
from app.features.volume_report.extraction.evm_parser import ParsedEvm, parse_evm_sheet
from app.features.volume_report.extraction.income_totals import IncomeTotals, detect_basis, parse_income_totals

from app.features.volume_report.extraction.income_parser import ParsedSheet, parse_income_sheet
from app.features.volume_report.extraction.normalize import Lexicon
from app.features.volume_report.extraction.pv_plan import ParsedPvPlan, parse_pv_plan
from app.features.volume_report.extraction.probe import SheetProbe, probe_workbook, suggest_company
from app.features.volume_report.extraction.workbook import open_workbook


@dataclass
class FileExtraction:
    sheet_log: list[dict[str, Any]] = field(default_factory=list)
    sheets: list[ParsedSheet] = field(default_factory=list)
    evm_sheets: list[ParsedEvm] = field(default_factory=list)
    income_totals: list[tuple[str, str, IncomeTotals]] = field(default_factory=list)  # (sheet, basis, totals)
    pv_plan: ParsedPvPlan | None = None
    suggested_company: str | None = None
    warnings: list[dict[str, Any]] = field(default_factory=list)


def _log_entry(probe: SheetProbe, parsed: ParsedSheet | None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "sheet": probe.sheet,
        "visibility": probe.visibility,
        "kind": probe.kind,
        "used": probe.used,
        "reason": probe.reason,
    }
    if parsed is not None:
        entry.update(
            used=parsed.status == "ok",
            reason=None if parsed.status == "ok" else parsed.status,
            basis=parsed.basis,
            site_name=parsed.site_name,
            rows_total=parsed.rows_total,
            rows_nonzero=parsed.rows_nonzero,
            rows_nonphysical=parsed.rows_nonphysical,
            header_row=parsed.header_row,
            columns=parsed.columns,
        )
        if parsed.status == "layout_unknown":
            entry["layout_unknown"] = True
    return entry


def _unreadable(rows: list[list[Any]]) -> bool:
    text = "".join(str(c) for row in rows for c in row if c is not None)
    controls = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\t\r")
    return len(text) >= 20 and controls / len(text) > 0.15


def extract_file(
    path: str, lexicon: Lexicon, period_label: str | None = None, layout_overrides: dict[str, dict] | None = None,
    force_planned: bool = False,
    pv_only: bool = False,
    evm_only: bool = False,
) -> FileExtraction:
    """Blocking (file I/O): run in a worker/thread."""
    result = FileExtraction()
    last_income: ParsedSheet | None = None
    with open_workbook(path) as workbook:
        probes = probe_workbook(workbook)
        result.suggested_company = suggest_company(workbook, probes)
        for sheet, probe in zip(workbook.sheets, probes):
            if pv_only:
                # A monthly PV plan file: only its PV sheet is read (the company-wide EVM workbook has dozens of other sheets).
                plan = None if sheet.is_hidden else parse_pv_plan(sheet.name, sheet.rows())
                if plan is not None and result.pv_plan is None:
                    result.pv_plan = plan
                result.sheet_log.append({
                    "sheet": probe.sheet, "visibility": probe.visibility, "kind": "pv_plan" if plan is not None else "other",
                    "used": plan is not None, "reason": None if plan is not None else "not_pv_plan_sheet",
                    "pv_rows": len(plan.rows) if plan is not None else None, "basis": "planned",
                })
                continue
            evm = None if sheet.is_hidden else parse_evm_sheet(sheet.name, sheet.rows(), os.path.basename(path), period_label)
            if evm is not None:
                # The EVM summary (PV/EV/AC/CPI/SPI per project) is its own data set, never an income table.
                if force_planned:
                    evm.basis = "planned"
                result.evm_sheets.append(evm)
                result.warnings.extend({**w, "sheet": sheet.name} for w in evm.warnings)
                result.sheet_log.append({
                    "sheet": probe.sheet, "visibility": probe.visibility, "kind": "evm", "used": True, "reason": None,
                    "basis": evm.basis, "evm_rows": len(evm.rows), "header_row": evm.header_row,
                })
                continue
            if not sheet.is_hidden:
                totals = parse_income_totals(sheet.rows())
                if totals is not None:
                    totals_basis = "planned" if force_planned else detect_basis(sheet.name, sheet.rows(), os.path.basename(path), period_label)
                    result.income_totals.append((sheet.name, totals_basis, totals))
            if not sheet.is_hidden and probe.kind == "other" and _unreadable(sheet.rows()):
                # Broken font encoding: the PDF holds control characters instead of letters, nothing can be read from it.
                if not any(w.get("code") == "unreadable_pdf_font" for w in result.warnings):
                    result.warnings.append({"code": "unreadable_pdf_font"})
                result.sheet_log.append({"sheet": probe.sheet, "visibility": probe.visibility, "kind": "other", "used": False, "reason": "unreadable_font"})
                continue
            # A forecast file ("پیش بینی" in its name or title) keeps plain "درآمد …" sheet names: those are still the forecast.
            if evm_only:
                continue  # re-reading only the EVM / income-totals / PV-plan rows: no income lines, nothing for the classification
            basis = "planned" if force_planned or probe.kind == "planned" or detect_basis(sheet.name, sheet.rows(), os.path.basename(path), period_label) == "planned" else "actual"
            parsed = parse_income_sheet(
                sheet.name, sheet.rows(), lexicon, period_label, (layout_overrides or {}).get(sheet.name), basis,
            ) if probe.used else None
            continuation = False
            if (parsed is None or parsed.status == "layout_unknown") and last_income is not None:
                # A headerless page that carries on the previous project's table (whatever its name says: "هزینه", "صفحه", …).
                grid = continuation_grid(sheet.rows())
                if grid is not None:
                    parsed = parse_income_sheet(sheet.name, grid, lexicon, None, None, last_income.basis)
                    parsed.site_name, parsed.site_name_norm, parsed.site_kind_guess = last_income.site_name, last_income.site_name_norm, last_income.site_kind_guess
                    continuation = True
            if parsed is not None and parsed.status == "ok" and not continuation:
                last_income = parsed
            if parsed is not None and probe.kind == "planned" and parsed.status != "ok":
                # A forecast sheet we cannot read is never worth a layout question: the actuals do not depend on it.
                entry = _log_entry(probe, parsed)
                entry.update(used=False, reason="planned_layout_unknown")
                entry.pop("layout_unknown", None)
                result.sheet_log.append(entry)
                continue
            if parsed is not None:
                result.sheets.append(parsed)
                result.warnings.extend({**w, "sheet": sheet.name} for w in parsed.warnings)
            entry = _log_entry(probe, parsed)
            if continuation:
                entry.update(kind="planned" if parsed.basis == "planned" else "income", continuation=True)
            if probe.used and (layout_overrides or {}).get(sheet.name):
                entry["layout_override"] = layout_overrides[sheet.name]  # kept so a re-run applies the confirmed layout again
            result.sheet_log.append(entry)
    return result


def suggest_kind_for_file(path: str) -> tuple[str, int | None]:
    """Cheap probe for the wizard (blocking): ("monthly_pv" | "monthly_plan" | "period", Jalali month or None)."""
    from app.features.volume_report.extraction.plan_month import detect_plan_month
    from app.features.volume_report.extraction.pv_plan import detect_pv_plan

    pv_plan = detect_pv_plan(path)
    if pv_plan is not None:
        return "monthly_pv", pv_plan.month
    month = detect_plan_month(path)
    return ("monthly_plan", month) if month else ("period", None)


def suggest_company_for_file(path: str) -> str | None:
    """Cheap probe for the wizard (blocking): only the summary-sheet company hint."""
    with open_workbook(path) as workbook:
        return suggest_company(workbook, probe_workbook(workbook))


def read_sheet_rows(path: str, sheet_name: str) -> list[list]:
    """Rows of one sheet (blocking). Callers must mask numeric cells before showing them to a model."""
    with open_workbook(path) as workbook:
        for sheet in workbook.sheets:
            if sheet.name == sheet_name:
                return sheet.rows()
    return []
