"""Unit conversion over a small graph of edges, each possibly needing a parameter. Decimal arithmetic only."""

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

# (from, to) -> (param key | None, operation). Operations are applied to the Decimal quantity.
_EDGES: dict[tuple[str, str], tuple[str | None, str]] = {
    ("kg", "t"): (None, "div1000"),
    ("t", "kg"): (None, "mul1000"),
    ("m2cm", "m3"): (None, "div100"),
    ("m3", "t"): ("density_t_per_m3", "mul"),
    ("t", "m3"): ("density_t_per_m3", "div"),
    ("m2", "m3"): ("thickness_m", "mul"),
    ("m", "m3"): ("cross_section_m2", "mul"),
}
_ADJACENT: dict[str, list[str]] = {}
for _src, _dst in _EDGES:
    _ADJACENT.setdefault(_src, []).append(_dst)

# Density conversion between mass and volume is valid for t <-> m3 only (e.g. asphalt, mining load).
# Direct chaining of kg to/from m3 is disallowed (e.g. kg on concrete is an invalid unit, not convertible).
_DISALLOWED_PATHS: set[tuple[str, str]] = {("kg", "m3"), ("m3", "kg")}


@dataclass(frozen=True)
class ConversionOutcome:
    status: str  # ok | unit_mismatch | no_conversion
    quantity: Decimal | None = None
    missing_param: str | None = None


def find_path(source: str, target: str) -> list[tuple[str, str]] | None:
    """Shortest edge path source -> target (BFS), [] when equal, None when unreachable."""
    if source == target:
        return []
    if (source, target) in _DISALLOWED_PATHS:
        return None
    seen, queue = {source}, deque([(source, [])])
    while queue:
        node, path = queue.popleft()
        for nxt in _ADJACENT.get(node, ()):
            if nxt in seen or (source, nxt) in _DISALLOWED_PATHS:
                continue
            new_path = path + [(node, nxt)]
            if nxt == target:
                return new_path
            seen.add(nxt)
            queue.append((nxt, new_path))
    return None


def convert_quantity(quantity: Decimal, source: str, target: str, params: dict[str, Decimal]) -> ConversionOutcome:
    """`params` maps param key -> value already resolved for this (site, item) by priority."""
    path = find_path(source, target)
    if path is None:
        return ConversionOutcome("unit_mismatch")
    value = quantity
    for edge in path:
        key, op = _EDGES[edge]
        if key is not None and key not in params:
            return ConversionOutcome("no_conversion", missing_param=key)
        if op == "div1000":
            value = value / 1000
        elif op == "mul1000":
            value = value * 1000
        elif op == "div100":
            value = value / 100
        elif op == "div":
            param_val = params[key]
            if not param_val:
                return ConversionOutcome("no_conversion", missing_param=key)
            value = value / param_val
        else:
            value = value * params[key]
    return ConversionOutcome("ok", quantity=value)
