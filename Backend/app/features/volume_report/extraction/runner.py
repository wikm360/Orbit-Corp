"""File-level extraction: probe every sheet, parse the income ones, build the `sheet_log` stored on `vr_report_files`."""

from dataclasses import dataclass, field
from typing import Any

from app.features.volume_report.extraction.income_parser import ParsedSheet, parse_income_sheet
from app.features.volume_report.extraction.normalize import Lexicon
from app.features.volume_report.extraction.probe import SheetProbe, probe_workbook, suggest_company
from app.features.volume_report.extraction.workbook import open_workbook


@dataclass
class FileExtraction:
    sheet_log: list[dict[str, Any]] = field(default_factory=list)
    sheets: list[ParsedSheet] = field(default_factory=list)
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


def extract_file(
    path: str, lexicon: Lexicon, period_label: str | None = None, layout_overrides: dict[str, dict] | None = None
) -> FileExtraction:
    """Blocking (file I/O): run in a worker/thread."""
    result = FileExtraction()
    with open_workbook(path) as workbook:
        probes = probe_workbook(workbook)
        result.suggested_company = suggest_company(workbook, probes)
        for sheet, probe in zip(workbook.sheets, probes):
            parsed = parse_income_sheet(
                sheet.name, sheet.rows(), lexicon, period_label, (layout_overrides or {}).get(sheet.name),
                "planned" if probe.kind == "planned" else "actual",
            ) if probe.used else None
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
            if probe.used and (layout_overrides or {}).get(sheet.name):
                entry["layout_override"] = layout_overrides[sheet.name]  # kept so a re-run applies the confirmed layout again
            result.sheet_log.append(entry)
    return result


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
