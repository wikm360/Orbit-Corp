import numpy as np
from PIL import Image, ImageDraw

from app.features.documents.ingestion import image_preprocess as pp


def _ruled_page(width=900, height=1200, bg=245, ink=30) -> Image.Image:
    """White page with horizontal text-like rules (a stand-in for lines of text / table borders)."""
    page = Image.new("L", (width, height), bg)
    draw = ImageDraw.Draw(page)
    for y in range(150, height - 150, 40):
        draw.rectangle((100, y, width - 100, y + 8), fill=ink)
    return page.convert("RGB")


def test_blank_pages_are_blank_but_sparse_or_faint_pages_are_not():
    rng = np.random.default_rng(0)
    noisy_white = Image.fromarray((250 + rng.normal(0, 2, (1000, 800))).clip(0, 255).astype(np.uint8)).convert("RGB")
    assert pp.is_blank(Image.new("RGB", (800, 1000), "white"))
    assert pp.is_blank(noisy_white)
    assert not pp.is_blank(_ruled_page())
    assert not pp.is_blank(_ruled_page(bg=245, ink=200))  # washed-out scan: strokes only 45 levels darker
    inverted = Image.fromarray(255 - np.asarray(_ruled_page().convert("L"))).convert("RGB")
    assert not pp.is_blank(inverted)  # light text on a dark page


def test_estimate_skew_recovers_a_known_rotation():
    page = _ruled_page()
    for applied in (-4.0, -1.5, 2.0, 5.0):
        skewed = page.rotate(applied, expand=True, fillcolor=(245, 245, 245))
        assert abs(pp.estimate_skew(skewed) + applied) < 0.35  # the correction is the opposite rotation


def test_deskew_leaves_a_straight_page_alone_and_straightens_a_skewed_one():
    page = _ruled_page()
    assert pp.deskew(page) is page
    skewed = page.rotate(3.0, expand=True, fillcolor=(245, 245, 245))
    assert abs(pp.estimate_skew(pp.deskew(skewed))) < 0.4


def test_crop_margins_removes_empty_border_but_keeps_a_full_page():
    page = Image.new("RGB", (1000, 1400), "white")
    ImageDraw.Draw(page).rectangle((150, 250, 850, 1150), fill="black")
    cropped = pp.crop_margins(page)
    assert cropped.width < 800 and cropped.height < 1000
    assert cropped.width >= 700 and cropped.height >= 900  # content (700x900) plus padding is kept

    tiny = Image.new("RGB", (1000, 1400), "white")
    ImageDraw.Draw(tiny).rectangle((300, 400, 700, 900), fill="black")
    assert pp.crop_margins(tiny).size == tiny.size  # would drop >70% of the page: more likely a mis-detection

    full = _ruled_page(bg=245)
    assert pp.crop_margins(full).size[0] >= int(full.size[0] * 0.7)  # nothing important is lost


def test_split_vertical_covers_the_page_with_overlap():
    page = Image.new("RGB", (500, 1000), "white")
    parts = pp.split_vertical(page, 2, overlap_ratio=0.1)
    assert len(parts) == 2 and all(p.width == 500 for p in parts)
    assert parts[0].height + parts[1].height > 1000  # overlapping bands
