"""Deterministic resolve -> convert -> aggregate over plain data (no DB, no LLM). The service loads rows into these
dataclasses and writes the outcome back, so every rule here is unit-testable.

Each non-zero line ends with exactly one `effect`; nothing is silently dropped (see `check_conservation`)."""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.features.volume_report.convert import convert_quantity

_Q = Decimal("0.0001")


@dataclass
class LineIn:
    id: str
    site_id: str
    site_kind: str
    group_key: str
    unit_norm: str
    quantity: Decimal
    negative: bool = False
    description_norm: str = ""


@dataclass
class RuleIn:
    """Item rule: lines of `item_key` whose description contains any phrase (and whose unit is `source_unit`) are
    converted as `quantity * factor` straight into the item's output unit, bypassing the generic conversion graph."""

    id: str
    item_key: str
    phrases: list[str]
    source_unit: str
    factor: Decimal
    site_id: str | None = None
    priority: int = 0
    note: str | None = None


@dataclass
class ClassIn:
    disposition: str  # counted | excluded | nonphysical | unmatched | needs_input
    item_key: str | None = None
    role: str = "na"
    exclude_reason: str | None = None
    confirmed: bool = False


@dataclass
class ItemIn:
    key: str
    output_unit: str
    mining_only: bool = False
    is_rollup: bool = False
    rollup_of: list[str] = field(default_factory=list)


@dataclass
class LineOut:
    line_id: str
    effect: str
    item_key: str | None = None
    output_qty: Decimal | None = None
    output_unit: str | None = None
    note: str | None = None
    unconfirmed: bool = False
    # Unrounded converted quantity: totals are summed from this so per-line rounding never accumulates.
    exact: Decimal | None = None


@dataclass
class ResultOut:
    scope: str
    company_id: str | None
    site_id: str | None
    item_key: str
    qty: Decimal
    unit: str
    n_lines: int
    has_unconfirmed: bool


def _param_lookup(params: list[dict[str, Any]], site_id: str, item_key: str) -> dict[str, Decimal]:
    """params rows: {key, item_key|None, site_id|None, value}. Priority: site+item > item > global."""
    best: dict[str, tuple[int, Decimal]] = {}
    for p in params:
        if p["site_id"] not in (None, site_id) or p["item_key"] not in (None, item_key):
            continue
        rank = (2 if p["site_id"] else 0) + (1 if p["item_key"] else 0)
        if p["key"] not in best or rank > best[p["key"]][0]:
            best[p["key"]] = (rank, Decimal(p["value"]))
    return {k: v for k, (_, v) in best.items()}


def match_rule(rules: list[RuleIn], line: LineIn, item_key: str) -> RuleIn | None:
    """Best rule for a line: site-specific beats global, then higher priority, then id for determinism."""
    hits = [
        r for r in rules
        if r.item_key == item_key and r.source_unit == line.unit_norm and r.site_id in (None, line.site_id)
        and any(p and p in line.description_norm for p in r.phrases)
    ]
    if not hits:
        return None
    return max(hits, key=lambda r: (r.site_id is not None, r.priority, r.id))


def resolve_lines(
    lines: list[LineIn], classes: dict[str, ClassIn], items: dict[str, ItemIn], params: list[dict[str, Any]],
    rules: list[RuleIn] | None = None,
) -> list[LineOut]:
    outs: dict[str, LineOut] = {}
    candidates: dict[tuple[str, str], list[tuple[LineIn, ClassIn]]] = defaultdict(list)

    for line in lines:
        cls = classes.get(line.group_key)
        if cls is None:
            outs[line.id] = LineOut(line.id, "needs_input", note="no_classification", unconfirmed=True)
            continue
        flag = not cls.confirmed
        d = cls.disposition
        if d == "excluded":
            effect = "duplicate_ignored" if cls.exclude_reason == "duplicate" else "excluded"
            outs[line.id] = LineOut(line.id, effect, note=cls.exclude_reason)
        elif d == "nonphysical":
            outs[line.id] = LineOut(line.id, "nonphysical")
        elif d == "unmatched":
            outs[line.id] = LineOut(line.id, "unmatched", unconfirmed=flag)
        elif d == "needs_input":
            outs[line.id] = LineOut(line.id, "needs_input", unconfirmed=True)
        elif d == "counted":
            item = items.get(cls.item_key or "")
            if item is None or item.is_rollup:
                outs[line.id] = LineOut(line.id, "needs_input", note="invalid_item", unconfirmed=True)
            elif line.negative:
                # Deductions ("کسورات") are kept for visibility but never subtracted without an explicit decision.
                outs[line.id] = LineOut(line.id, "excluded", item.key, note="negative_qty", unconfirmed=flag)
            elif item.mining_only and line.site_kind != "mining":
                outs[line.id] = LineOut(line.id, "site_kind_mismatch", item.key, unconfirmed=flag)
            else:
                candidates[(line.site_id, item.key)].append((line, cls))
        else:
            outs[line.id] = LineOut(line.id, "needs_input", note="unknown_disposition", unconfirmed=True)

    for (site_id, item_key), pool in candidates.items():
        item = items[item_key]
        has_execution = any(c.role != "supply" for _, c in pool)
        for line, cls in pool:
            flag = not cls.confirmed
            if cls.role == "supply":
                effect = "supply_ignored" if has_execution else "supply_only_not_counted"
                outs[line.id] = LineOut(line.id, effect, item_key, unconfirmed=flag)
                continue
            rule = match_rule(rules, line, item_key) if rules else None
            if rule is not None:
                exact = line.quantity * rule.factor
                outs[line.id] = LineOut(
                    line.id, "counted", item_key, exact.quantize(_Q, ROUND_HALF_UP), item.output_unit,
                    note=f"rule:{rule.id}", unconfirmed=flag, exact=exact,
                )
                continue
            outcome = convert_quantity(line.quantity, line.unit_norm, item.output_unit, _param_lookup(params, site_id, item_key))
            if outcome.status == "ok":
                outs[line.id] = LineOut(
                    line.id, "counted", item_key, outcome.quantity.quantize(_Q, ROUND_HALF_UP), item.output_unit,
                    unconfirmed=flag, exact=outcome.quantity,
                )
            else:
                outs[line.id] = LineOut(
                    line.id, outcome.status, item_key, note=outcome.missing_param or f"{line.unit_norm}->{item.output_unit}", unconfirmed=flag
                )
    return [outs[line.id] for line in lines]


def check_conservation(lines: list[LineIn], outs: list[LineOut]) -> str | None:
    """Every line has exactly one effect (so per-unit raw totals equal the sum over all effects). Returns an error text on a bug."""
    ids = [o.line_id for o in outs]
    if len(ids) != len(set(ids)) or set(ids) != {line.id for line in lines}:
        return "Quantity conservation check failed: lines and results differ."
    return None


def aggregate(
    lines: list[LineIn], outs: list[LineOut], items: dict[str, ItemIn], site_company: dict[str, str]
) -> list[ResultOut]:
    by_line = {line.id: line for line in lines}
    cells: dict[tuple[str, str], list] = defaultdict(lambda: [Decimal(0), 0, False])  # (site, item) -> qty, n, unconfirmed
    for out in outs:
        if out.effect != "counted" or out.output_qty is None:
            continue
        cell = cells[(by_line[out.line_id].site_id, out.item_key)]
        cell[0] += out.exact if out.exact is not None else out.output_qty
        cell[1] += 1
        cell[2] = cell[2] or out.unconfirmed

    # Rollups are built from the already-converted member totals, never from raw lines again.
    for item in items.values():
        if not item.is_rollup:
            continue
        for site_id in {s for s, _ in list(cells)}:
            parts = [cells[(site_id, k)] for k in item.rollup_of if (site_id, k) in cells and items[k].output_unit == item.output_unit]
            if parts:
                cells[(site_id, item.key)] = [sum((p[0] for p in parts), Decimal(0)), sum(p[1] for p in parts), any(p[2] for p in parts)]

    results: list[ResultOut] = []
    company_cells: dict[tuple[str, str], list] = defaultdict(lambda: [Decimal(0), 0, False])
    holding_cells: dict[str, list] = defaultdict(lambda: [Decimal(0), 0, False])
    for (site_id, item_key), (qty, n, unconf) in cells.items():
        unit = items[item_key].output_unit
        results.append(ResultOut("site", site_company[site_id], site_id, item_key, qty.quantize(_Q, ROUND_HALF_UP), unit, n, unconf))
        for cell in (company_cells[(site_company[site_id], item_key)], holding_cells[item_key]):
            cell[0] += qty
            cell[1] += n
            cell[2] = cell[2] or unconf
    for (company_id, item_key), (qty, n, unconf) in company_cells.items():
        results.append(ResultOut("company", company_id, None, item_key, qty.quantize(_Q, ROUND_HALF_UP), items[item_key].output_unit, n, unconf))
    for item_key, (qty, n, unconf) in holding_cells.items():
        results.append(ResultOut("holding", None, None, item_key, qty.quantize(_Q, ROUND_HALF_UP), items[item_key].output_unit, n, unconf))
    return results
