"""Evaluate image pre-processing variants against the reviewed ground truth (eval/ground_truth.md).

    LLM_VISION_MODEL=gemini-flash-lite-latest python -m tools.ocr_eval.run --out <dir> --variants baseline deskew crop --runs 2

Every variant turns the original PIL image into one or more PIL images, which go through the project's own
`extract_text_from_image` (so the real optimize/resize/JPEG step and prompt are part of the measurement).
Results: <out>/<variant>/<image>.run<N>.md and <out>/results.json. Costs real vision-API calls.
"""

import argparse
import asyncio
import io
import json
import statistics
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.features.documents.ingestion import image_preprocess as pp  # noqa: E402
from app.features.documents.ingestion.ocr import extract_text_from_image  # noqa: E402
from tools.ocr_eval.keys import has_repetition_loop, score_image  # noqa: E402

IMAGES = ["Dropped Image", "Dropped Image (2)", "Dropped Image (3)", "Dropped Image (4)"]


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def rot(angle):  # counter-clockwise, like PIL
    return lambda im, name: [im.rotate(angle, expand=True, fillcolor=(255, 255, 255))]


def skew(angle):
    return lambda im, name: [im.rotate(angle, expand=True, fillcolor=(255, 255, 255))]


def skew_then_fix(angle):
    return lambda im, name: [pp.deskew(im.rotate(angle, expand=True, fillcolor=(255, 255, 255)))]


def upright_1(im, name):  # image 1 is scanned 90 degrees turned; the others are upright
    return [im.rotate(90, expand=True)] if name == "Dropped Image" else [im]


# name -> (function(im, image_name) -> list[Image], settings overrides)
VARIANTS = {
    "baseline": (lambda im, n: [im], {}),
    "upright": (upright_1, {}),
    "rot90": (rot(90), {}),
    "rot180": (rot(180), {}),
    "rot270": (rot(270), {}),
    "skew+3": (skew(3), {}),
    "skew-5": (skew(-5), {}),
    "skew+3_fixed": (skew_then_fix(3), {}),
    "skew-5_fixed": (skew_then_fix(-5), {}),
    "deskew": (lambda im, n: [pp.deskew(upright_1(im, n)[0])], {}),
    "crop": (lambda im, n: [pp.crop_margins(upright_1(im, n)[0])], {}),
    "contrast": (lambda im, n: [pp.enhance_contrast(upright_1(im, n)[0])], {}),
    "flatten": (lambda im, n: [pp.normalize_background(upright_1(im, n)[0])], {}),
    "dim1600": (lambda im, n: [upright_1(im, n)[0]], {"ocr_max_image_dimension": 1600}),
    "dim3200": (lambda im, n: [upright_1(im, n)[0]], {"ocr_max_image_dimension": 3200}),
    "upscale2x": (lambda im, n: [upright_1(im, n)[0].resize((im.width * 2, im.height * 2), Image.Resampling.LANCZOS)],
                  {"ocr_max_image_dimension": 3200}),
    "q100": (lambda im, n: [upright_1(im, n)[0]], {"ocr_jpeg_quality": 100}),
    "split2": (lambda im, n: pp.split_vertical(upright_1(im, n)[0], 2), {}),
    "dc": (lambda im, n: [pp.crop_margins(pp.deskew(upright_1(im, n)[0]))], {}),
    "dcq": (lambda im, n: [pp.crop_margins(pp.deskew(upright_1(im, n)[0]))], {"ocr_jpeg_quality": 100}),
    "combo": (lambda im, n: [pp.enhance_contrast(pp.crop_margins(pp.deskew(upright_1(im, n)[0])))], {}),
}


async def run_variant(name: str, fn, overrides: dict, image_name: str, run: int, out: Path, sem) -> dict:
    settings = get_settings()
    img = Image.open(ROOT / "eval" / f"{image_name}.png").convert("RGB")
    parts = fn(img, image_name)
    saved = {k: getattr(settings, k) for k in overrides}
    for k, v in overrides.items():
        setattr(settings, k, v)
    started = time.monotonic()
    try:
        async with sem:
            texts = [await extract_text_from_image(_png(p), "png") for p in parts]
    finally:
        for k, v in saved.items():
            setattr(settings, k, v)
    text = "\n\n".join(texts)
    found, total, detail = score_image(image_name, text)
    folder = out / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{image_name}.run{run}.md").write_text(text, encoding="utf-8")
    res = {"variant": name, "image": image_name, "run": run, "found": found, "total": total, "detail": detail,
           "chars": len(text), "loop": has_repetition_loop(text), "seconds": round(time.monotonic() - started, 1)}
    print(json.dumps(res, ensure_ascii=False), flush=True)
    return res


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--variants", nargs="+", default=["baseline"])
    ap.add_argument("--images", nargs="*", default=IMAGES)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--concurrency", type=int, default=6)
    args = ap.parse_args()
    sem = asyncio.Semaphore(args.concurrency)
    tasks = [run_variant(v, *VARIANTS[v], img, r, args.out, sem)
             for v in args.variants for img in args.images for r in range(args.runs)]
    results = await asyncio.gather(*tasks)
    results_file = args.out / "results.json"
    previous = json.loads(results_file.read_text()) if results_file.exists() else []
    results_file.write_text(json.dumps(previous + results, ensure_ascii=False, indent=1))

    print("\nvariant        " + "  ".join(f"{i[-9:]:>9}" for i in args.images) + "     mean")
    for v in args.variants:
        cells, fracs = [], []
        for img in args.images:
            rs = [r for r in results if r["variant"] == v and r["image"] == img]
            f = statistics.mean(r["found"] / r["total"] for r in rs) if rs else 0
            fracs.append(f)
            cells.append(f"{f:9.3f}")
        print(f"{v:14} " + "  ".join(cells) + f"  {statistics.mean(fracs):7.3f}")


if __name__ == "__main__":
    asyncio.run(main())
