"""Unit normalization (appendix B). Output is a closed set so downstream conversion never sees free text."""

import re
from dataclasses import dataclass

from app.core.text_normalization import normalize

# unit_norm -> dimension
UNIT_DIMENSIONS: dict[str, str] = {
    "m3": "volume",
    "m2": "area",
    "m": "length",
    "kg": "mass",
    "t": "mass",
    "m2cm": "area_thickness",
    "m3km": "volume_distance",
    "hr": "time",
    "lump": "nonphysical",
    "series": "nonphysical",
    "pct": "nonphysical",
    "ea": "nonphysical",
    "other": "nonphysical",
}

# Keys have all whitespace removed (see `_squash`), so "متر مکعب", "مترمکعب" and "متر\nمکعب" are one entry.
_EXACT: dict[str, str] = {
    "مترمکعب": "m3", "m3": "m3", "متر3": "m3", "cubicmeter": "m3",
    "مترمربع": "m2", "m2": "m2", "متر2": "m2", "squaremeter": "m2",
    "مترطول": "m", "مترطولی": "m", "متر": "m", "m": "m", "ml": "m",
    "کیلوگرم": "kg", "kg": "kg", "کیلو": "kg",
    "تن": "t", "ton": "t", "tonne": "t", "t": "t",
    "hr": "hr", "h": "hr", "ساعت": "hr",
    "مقطوع": "lump",
    "سری": "series",
    "درصد": "pct", "pct": "pct",
    "عدد": "ea", "شاخه": "ea", "فصل": "ea",
}


@dataclass(frozen=True)
class UnitInfo:
    unit_norm: str
    unit_dim: str
    empty: bool = False


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", normalize(text.replace("%", " درصد ").replace("²", "2").replace("³", "3")))


def normalize_unit(raw: object) -> UnitInfo:
    """Empty unit -> `other` with `empty=True` so the parser can warn; anything unknown is `other` (nonphysical)."""
    text = "" if raw is None else str(raw)
    key = _squash(text)
    if not key:
        return UnitInfo("other", UNIT_DIMENSIONS["other"], empty=True)
    # RTL PDF extraction reverses Latin+digit units: "m3" arrives as "3 m" (squashed "3m"), "m2" as "2m".
    key = re.sub(r"^(\d)(m|cm)$", r"\2\1", key)
    unit = _EXACT.get(key)
    if unit is None:
        # Compound units come with endless spacing/hyphen variants; match on the squashed key.
        if "مربع" in key and "سانتی" in key:
            unit = "m2cm"
        elif "مکعب" in key and "کیلومتر" in key:
            unit = "m3km"
        else:
            unit = "other"
    return UnitInfo(unit, UNIT_DIMENSIONS[unit])
