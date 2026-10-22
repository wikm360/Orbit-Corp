"""Manual experiment: OCR one image with Google Cloud Vision (DOCUMENT_TEXT_DETECTION) and print the result.

    pip install google-cloud-vision
    python tools/google_vision_ocr_test.py "eval/Dropped Image.png"
    python tools/google_vision_ocr_test.py "eval/Dropped Image.png" --key orbitcorp-xxxx.json --lang fa en

Not part of the app: the ingestion pipeline still uses the LLM vision model (see app/features/documents/ingestion/ocr.py).
Compare the output with `extract_text_from_image` on the same file to judge quality/cost.
"""

import argparse
import sys
import time
from pathlib import Path

from google.cloud import vision

ROOT = Path(__file__).resolve().parent.parent


def default_key() -> Path | None:
    keys = sorted(ROOT.glob("orbitcorp-*.json"))
    return keys[0] if keys else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", type=Path)
    parser.add_argument("--key", type=Path, default=default_key(), help="service-account JSON (default: ./orbitcorp-*.json)")
    parser.add_argument("--lang", nargs="*", default=["fa", "en"], help="language hints (default: fa en)")
    parser.add_argument("--out", type=Path, help="also write the text to this file")
    args = parser.parse_args()

    if not args.key or not args.key.exists():
        print("service-account key not found; pass --key", file=sys.stderr)
        return 2
    if not args.image.exists():
        print(f"image not found: {args.image}", file=sys.stderr)
        return 2

    client = vision.ImageAnnotatorClient.from_service_account_file(str(args.key))
    image = vision.Image(content=args.image.read_bytes())
    context = vision.ImageContext(language_hints=args.lang)

    started = time.monotonic()
    response = client.document_text_detection(image=image, image_context=context)
    elapsed = time.monotonic() - started

    if response.error.message:
        print(f"API error: {response.error.message}", file=sys.stderr)
        return 1

    annotation = response.full_text_annotation
    text = annotation.text
    confidences = [block.confidence for page in annotation.pages for block in page.blocks]
    langs = sorted(
        {lang.language_code for page in annotation.pages for lang in page.property.detected_languages}
    )

    print(f"--- {args.image.name}: {elapsed:.2f}s, {len(text)} chars, {len(confidences)} blocks, languages={langs}")
    if confidences:
        print(f"--- block confidence: mean={sum(confidences) / len(confidences):.3f} min={min(confidences):.3f}")
    print(text)

    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"--- written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
