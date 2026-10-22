"""Manual experiment: OCR one image/PDF with Mistral's document OCR API and print the Markdown it returns.

    python tools/mistral_ocr_test.py "eval/Dropped Image.png"
    python tools/mistral_ocr_test.py eval/10.pdf --out /tmp/out.md

The key is read from `mistral_key` (or MISTRAL_API_KEY) in the environment or in Backend/.env.
Not part of the app: the ingestion pipeline still uses the LLM vision model (app/features/documents/ingestion/ocr.py).
"""

import argparse
import base64
import io
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
API_URL = "https://api.mistral.ai/v1/ocr"


def load_key() -> str | None:
    for name in ("MISTRAL_API_KEY", "mistral_key", "MISTRAL_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip().lower() in ("mistral_api_key", "mistral_key"):
                return value.strip().strip("\"'")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--model", default="mistral-ocr-latest")
    parser.add_argument("--out", type=Path, help="also write the Markdown to this file")
    parser.add_argument("--rotate", type=int, default=0, choices=(0, 90, 180, 270),
                        help="rotate an image counter-clockwise before sending (Mistral's layout detection drops most of a rotated page)")
    parser.add_argument("--raw", type=Path, help="write the full JSON response (blocks, header/footer, usage) to this file")
    args = parser.parse_args()

    key = load_key()
    if not key:
        print("Mistral key not found (mistral_key in .env)", file=sys.stderr)
        return 2
    if not args.file.exists():
        print(f"file not found: {args.file}", file=sys.stderr)
        return 2

    mime = mimetypes.guess_type(args.file.name)[0] or "application/octet-stream"
    payload = args.file.read_bytes()
    if args.rotate and mime.startswith("image/"):
        from PIL import Image

        buf = io.BytesIO()
        Image.open(io.BytesIO(payload)).convert("RGB").rotate(args.rotate, expand=True).save(buf, format="PNG")
        payload, mime = buf.getvalue(), "image/png"
    data_url = f"data:{mime};base64,{base64.b64encode(payload).decode()}"
    if mime == "application/pdf":
        document = {"type": "document_url", "document_url": data_url}
    else:
        document = {"type": "image_url", "image_url": data_url}

    started = time.monotonic()
    response = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={"model": args.model, "document": document, "extract_header": True, "extract_footer": True, "include_blocks": True},
        timeout=180,
    )
    elapsed = time.monotonic() - started

    if response.status_code != 200:
        print(f"API error {response.status_code}: {response.text[:1000]}", file=sys.stderr)
        return 1

    body = response.json()
    if args.raw:
        args.raw.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    pages = body.get("pages", [])
    text = "\n\n".join(f"--- [page {p.get('index', i) + 1}] ---\n{p.get('markdown', '')}" for i, p in enumerate(pages))
    usage = body.get("usage_info", {})
    print(f"--- {args.file.name}: {elapsed:.2f}s, {len(pages)} page(s), {len(text)} chars, model={body.get('model')}, usage={usage}")
    print(text)

    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"--- written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
