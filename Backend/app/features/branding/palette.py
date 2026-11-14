"""Colour scales from one base colour. The base is the `500` shade; lighter shades mix toward white, darker toward black.
The three roles keep the Tailwind names the frontend already uses: `brand` (deep ground), `accent`, `teal` (= highlight)."""

import re

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
SHADES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)
_TO_WHITE = {50: 0.92, 100: 0.84, 200: 0.68, 300: 0.5, 400: 0.25}
_TO_BLACK = {600: 0.18, 700: 0.34, 800: 0.5, 900: 0.66}

# The palette the product shipped with (sampled from the first customer's logo): used verbatim while a base colour is unchanged,
# so an existing installation looks exactly as before. Shades not listed here are generated.
_KNOWN = {
    "#3446b8": {50: "#eef0fb", 100: "#dbdff6", 200: "#b7bfee", 300: "#8a97e2", 400: "#5b6bd3", 500: "#3446b8", 600: "#22309e", 700: "#182384", 800: "#121a66", 900: "#0c1247"},
    "#e8c523": {50: "#fefbe8", 100: "#fdf5c2", 300: "#f7e26b", 400: "#efd23a", 500: "#e8c523", 600: "#c9a70f", 700: "#9e820a"},
    "#25b8b4": {50: "#ebfcfb", 100: "#cbf7f4", 300: "#6fe2dc", 400: "#3fd0cb", 500: "#25b8b4", 600: "#1a9391", 700: "#177574"},
}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mix(base: tuple[int, int, int], target: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(b + (x - b) * t) for b, x in zip(base, target))  # type: ignore[return-value]


def luminance(rgb: tuple[int, int, int]) -> float:
    def channel(v: int) -> float:
        s = v / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_with_white(rgb: tuple[int, int, int]) -> float:
    return 1.05 / (luminance(rgb) + 0.05)


def scale(base_hex: str) -> dict[int, tuple[int, int, int]]:
    base = _rgb(base_hex)
    known = _KNOWN.get(base_hex.lower(), {})
    out: dict[int, tuple[int, int, int]] = {}
    for shade in SHADES:
        if shade in known:
            out[shade] = _rgb(known[shade])
        elif shade == 500:
            out[shade] = base
        elif shade in _TO_WHITE:
            out[shade] = _mix(base, (255, 255, 255), _TO_WHITE[shade])
        else:
            out[shade] = _mix(base, (0, 0, 0), _TO_BLACK[shade])
    return out


def css_scale(base_hex: str) -> dict[str, str]:
    """`{"500": "52 70 184", ...}`: the space-separated form Tailwind's `rgb(var(--x) / <alpha-value>)` needs."""
    return {str(shade): " ".join(str(v) for v in rgb) for shade, rgb in scale(base_hex).items()}


def is_default_base(hex_color: str) -> bool:
    return hex_color.lower() in _KNOWN


def button_contrast_ok(base_hex: str, minimum: float = 3.0) -> bool:
    """White text sits on the 600 shade of `brand` and `teal`: it must stay readable (WCAG 3:1 for UI components). The shipped
    colours are exempt (unchanged look)."""
    return is_default_base(base_hex) or contrast_with_white(scale(base_hex)[600]) >= minimum


def ground(brand_hex: str) -> dict[str, str]:
    """The dark surfaces (sidebar, primary button): the shipped navy-teal while `brand` is unchanged, else derived from `brand`."""
    if is_default_base(brand_hex) and brand_hex.lower() == "#3446b8":
        return {"base": "20 43 64", "button": "22 59 72"}
    sc = css_scale(brand_hex)
    return {"base": sc["900"], "button": sc["800"]}
