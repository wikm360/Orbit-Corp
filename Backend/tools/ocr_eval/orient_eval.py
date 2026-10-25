"""Evaluate page-orientation detection (`OCR_ORIENT_METHOD` = model | osd | hybrid) on upright pages rotated by 0/90/180/270.

    LLM_VISION_MODEL=gemini-flash-lite-latest python -m tools.ocr_eval.orient_eval \\
        --images "eval/Dropped Image (2).png" /tmp/pages/*.png --pre-rotate "Dropped Image.png=90" --methods osd hybrid model

Pass pages that are *upright* (use --pre-rotate to fix known sideways ones). For every page and rotation the chosen
rotation must undo it. Reports accuracy, vision-model calls (probes) and OSD calls per method. The `model` and
`hybrid` methods call the vision model (cheap, ~1.1k input tokens each); `osd` needs the `tesseract` binary.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.features.documents.ingestion import ocr as ocr_module  # noqa: E402
from app.features.documents.ingestion.image_orientation import choose_rotation, detect_rotation_osd  # noqa: E402


async def evaluate(
    method: str, pages: list[tuple[str, Image.Image]], sem: asyncio.Semaphore, min_conf: float, upright_conf: float
) -> None:
    counts = {"probe": 0, "osd": 0}

    async def probe(thumb):
        counts["probe"] += 1
        return await ocr_module._probe_rotation(thumb)

    async def osd(image):
        counts["osd"] += 1
        return await detect_rotation_osd(image)

    async def one(name, page, applied):
        scanned = page.rotate(applied, expand=True, fillcolor=(255, 255, 255))  # counter-clockwise
        async with sem:
            got = await choose_rotation(
                scanned, method=method, probe=probe, osd=osd, min_confidence=min_conf, upright_confidence=upright_conf
            )
        return name, applied, got

    results = await asyncio.gather(*(one(n, p, a) for n, p in pages for a in (0, 90, 180, 270)))
    wrong = [(n, a, g) for n, a, g in results if g != a]  # rotating CCW by `a` is undone by rotating CW by `a`
    harmful = [w for w in wrong if w[1] == 0]  # an upright page that was rotated
    print(f"{method:7} correct {len(results) - len(wrong)}/{len(results)}  upright pages wrongly rotated: {len(harmful)}  "
          f"model probes: {counts['probe']}  OSD runs: {counts['osd']}")
    for n, a, g in wrong:
        print(f"    wrong: {n} applied {a} -> chose {g}")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", nargs="+", type=Path, required=True)
    ap.add_argument("--pre-rotate", nargs="*", default=[], help="'<file name>=<ccw degrees>' for pages that are not upright")
    ap.add_argument("--methods", nargs="+", default=["osd", "hybrid", "model"])
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()
    pre = {k: int(v) for k, v in (item.rsplit("=", 1) for item in args.pre_rotate)}
    pages = []
    for path in args.images:
        img = Image.open(path).convert("RGB")
        if path.name in pre:
            img = img.rotate(pre[path.name], expand=True)
        pages.append((path.name, img))
    settings = get_settings()
    print(f"{len(pages)} pages x 4 rotations; model={settings.llm_vision_model or settings.llm_model}; "
          f"min OSD confidence {settings.ocr_orient_osd_min_confidence}, upright {settings.ocr_orient_osd_upright_confidence}")
    sem = asyncio.Semaphore(args.concurrency)
    for method in args.methods:
        await evaluate(
            method, pages, sem, settings.ocr_orient_osd_min_confidence, settings.ocr_orient_osd_upright_confidence
        )


if __name__ == "__main__":
    asyncio.run(main())
