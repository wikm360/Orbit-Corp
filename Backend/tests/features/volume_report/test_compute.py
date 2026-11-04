from decimal import Decimal

from app.features.volume_report import compute
from app.features.volume_report.compute import ClassIn, ItemIn, LineIn

ITEMS = {
    "subbase": ItemIn("subbase", "m3"),
    "binder": ItemIn("binder", "t"),
    "precast": ItemIn("precast", "m3"),
    "concrete": ItemIn("concrete", "m3"),
    "mining_load": ItemIn("mining_load", "m3", mining_only=True),
    "tack": ItemIn("tack", "kg"),
    "asphalt_total": ItemIn("asphalt_total", "t", is_rollup=True, rollup_of=["binder", "topka"]),
    "topka": ItemIn("topka", "t"),
}
DENSITY = [{"key": "density_t_per_m3", "item_key": None, "site_id": None, "value": "2.35"}]


def line(i, group, unit, qty, kind="road", site="s1", neg=False):
    return LineIn(i, site, kind, group, unit, Decimal(str(qty)), neg)


def run(lines, classes, params=()):
    outs = compute.resolve_lines(lines, classes, ITEMS, list(params))
    return {o.line_id: o for o in outs}, outs


def test_supply_ignored_when_execution_exists_and_not_counted_when_alone():
    lines = [line("a", "g1", "m3", 794.17), line("b", "g2", "m3", 1949.36), line("c", "g3", "m3", 10, site="s2")]
    classes = {"g1": ClassIn("counted", "subbase", "supply", confirmed=True), "g2": ClassIn("counted", "subbase", "execute", confirmed=True),
               "g3": ClassIn("counted", "subbase", "supply", confirmed=True)}
    by, _ = run(lines, classes)
    assert by["a"].effect == "supply_ignored" and by["b"].effect == "counted" and by["b"].output_qty == Decimal("1949.36")
    assert by["c"].effect == "supply_only_not_counted"


def test_asphalt_m2cm_to_tonnes_with_density_and_rollup():
    lines = [line("a", "g", "m2cm", 109483.9)]
    by, outs = run(lines, {"g": ClassIn("counted", "binder", "execute", confirmed=True)}, DENSITY)
    assert by["a"].output_qty == Decimal("2572.8717") and by["a"].output_unit == "t"
    results = compute.aggregate(lines, outs, ITEMS, {"s1": "c1"})
    cells = {(r.scope, r.item_key): r.qty for r in results}
    assert cells[("holding", "asphalt_total")] == cells[("holding", "binder")] == Decimal("2572.8717")


def test_kg_to_tonnes_and_unit_in_tonnes_passthrough():
    lines = [line("a", "g", "kg", 10490.18), line("b", "g2", "t", 693)]
    by, _ = run(lines, {"g": ClassIn("counted", "binder", "execute", True), "g2": ClassIn("counted", "binder", "execute", True)})
    assert by["a"].output_qty == Decimal("10.4902") and by["b"].output_qty == Decimal("693")


def test_unit_mismatch_and_no_conversion_never_silent():
    lines = [line("a", "g", "hr", 5), line("b", "g2", "m", 50), line("c", "g3", "t", 50, kind="mining")]
    classes = {"g": ClassIn("counted", "concrete", "execute", True), "g2": ClassIn("counted", "precast", "execute", True),
               "g3": ClassIn("counted", "mining_load", "execute", True)}
    by, _ = run(lines, classes)
    assert by["a"].effect == "unit_mismatch"
    assert by["b"].effect == "no_conversion" and by["b"].note == "cross_section_m2"
    assert by["c"].effect == "no_conversion" and by["c"].note == "density_t_per_m3"
    by2, _ = run(lines, classes, [{"key": "cross_section_m2", "item_key": "precast", "site_id": None, "value": "0.5"},
                                  {"key": "density_t_per_m3", "item_key": "mining_load", "site_id": None, "value": "2.0"}])
    assert by2["b"].effect == "counted" and by2["b"].output_qty == Decimal("25")
    assert by2["c"].effect == "counted" and by2["c"].output_qty == Decimal("25")


def test_parameter_priority_site_item_over_global():
    params = DENSITY + [{"key": "density_t_per_m3", "item_key": "binder", "site_id": None, "value": "2.4"},
                        {"key": "density_t_per_m3", "item_key": "binder", "site_id": "s1", "value": "2.5"}]
    by, _ = run([line("a", "g", "m3", 100)], {"g": ClassIn("counted", "binder", "execute", True)}, params)
    assert by["a"].output_qty == Decimal("250")


def test_mining_only_item_outside_mining_goes_to_mismatch():
    lines = [line("a", "g", "m3", 100, kind="mining"), line("b", "g", "m3", 7, kind="road", site="s2")]
    by, _ = run(lines, {"g": ClassIn("counted", "mining_load", "execute", True)})
    assert by["a"].effect == "counted" and by["b"].effect == "site_kind_mismatch"


def test_negative_never_subtracted_and_every_line_has_one_effect():
    lines = [line("a", "g", "m3", -72283, neg=True), line("b", "g2", "m3", 5), line("c", "gx", "m3", 1)]
    classes = {"g": ClassIn("counted", "mining_load", "execute", True, ), "g2": ClassIn("excluded", exclude_reason="duplicate", confirmed=True)}
    by, outs = run(lines, classes)
    assert by["a"].effect == "excluded" and by["a"].note == "negative_qty"
    assert by["b"].effect == "duplicate_ignored" and by["c"].effect == "needs_input"
    assert compute.check_conservation(lines, outs) is None
    assert compute.check_conservation(lines, outs[:-1]) is not None


def test_unconfirmed_flag_propagates_to_aggregates():
    lines = [line("a", "g", "m3", 3)]
    _, outs = run(lines, {"g": ClassIn("counted", "subbase", "execute", False)})
    assert all(r.has_unconfirmed for r in compute.aggregate(lines, outs, ITEMS, {"s1": "c1"}))


def _rule(**kw):
    base = dict(id="r1", item_key="concrete", phrases=["آبرو دالی"], source_unit="m2", factor=Decimal("2"))
    return compute.RuleIn(**{**base, **kw})


def _cline(i, desc, unit="m2", qty=10, site="s1"):
    return LineIn(i, site, "road", f"g_{i}", unit, Decimal(str(qty)), description_norm=desc)


def _run_rules(lines, rules):
    classes = {l.group_key: ClassIn("counted", "concrete", "execute", confirmed=True) for l in lines}
    return {o.line_id: o for o in compute.resolve_lines(lines, classes, ITEMS, [], rules)}


def test_item_rule_applies_factor_only_to_matching_lines():
    lines = [_cline("a", "ساخت آبرو دالی به دهانه 3 متر", qty=16), _cline("b", "عملیات احداث رادیه", qty=15)]
    by = _run_rules(lines, [_rule()])
    assert by["a"].effect == "counted" and by["a"].output_qty == Decimal("32.0000") and by["a"].output_unit == "m3"
    assert by["a"].note == "rule:r1"
    assert by["b"].effect == "no_conversion"  # no generic m2->m3 parameter, and the rule does not match


def test_item_rule_respects_unit_site_and_priority():
    same_unit = _cline("a", "آبرو دالی", unit="m3", qty=5)
    assert _run_rules([same_unit], [_rule()])["a"].output_qty == Decimal("5.0000")  # m3 line untouched by an m2 rule
    other_site = _cline("b", "آبرو دالی", site="s2")
    assert _run_rules([other_site], [_rule(site_id="s1")])["b"].effect == "no_conversion"
    line_ = _cline("c", "آبرو دالی")
    by = _run_rules([line_], [_rule(), _rule(id="r2", factor=Decimal("3"), priority=5)])
    assert by["c"].output_qty == Decimal("30.0000") and by["c"].note == "rule:r2"
    by = _run_rules([line_], [_rule(), _rule(id="r3", factor=Decimal("4"), site_id="s1")])
    assert by["c"].note == "rule:r3"  # site-specific beats global
