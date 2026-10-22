"""Manual experiment: run the project's vision-OCR prompt on the same images with several models of the configured
gateway (LLM_API_BASE_URL / LLM_API_KEY from Backend/.env) and save every output for side-by-side comparison.

    python tools/ocr_model_compare.py --out /tmp/ocr_cmp                      # default models x eval/Dropped Image*.png
    python tools/ocr_model_compare.py --out /tmp/ocr_cmp --models gemini-flash-lite-latest qwen3-omni-flash

Writes <out>/<model>/<image>.md and <out>/summary.json (seconds, tokens, chars, error per run).
Prices below are USD per 1M tokens (input, output) as listed by the gateway; the cost is only an estimate.
Not part of the app.
"""

import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.features.documents.ingestion.ocr import SYSTEM_OCR_PROMPT, optimize_image_for_ocr  # noqa: E402

PRICES = {
    "gemini-flash-lite-latest": None,  # not in the pasted price list
    "deepseek-v4-flash": (0.14, 0.28),
    "deepseek-v4-flash-vision-exp": (0.14, 0.14),
    "deepseek-v4.1-flash": (0.15, 0.60),
    "deepseek-v4.1-flash-uncensored": (0.0, 0.0),
    "Qwen/Qwen3.5-35B-A3B-FP8": (0.25, 2.00),
    "qwen3-omni-flash": (0.60, 2.40),
    "qwen3.8-27b-uncensored": (0.0, 0.0),
    "qwen3-235b-a22b": (0.16, 0.48),
}


async def run_one(client: AsyncOpenAI, model: str, image: Path, sem: asyncio.Semaphore, max_tokens: int) -> dict:
    optimized, mime = await asyncio.to_thread(optimize_image_for_ocr, image.read_bytes())
    b64 = base64.b64encode(optimized).decode()
    started = time.monotonic()
    result = {"model": model, "image": image.name, "seconds": None, "in_tokens": None, "out_tokens": None,
              "chars": 0, "error": None}
    async with sem:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": SYSTEM_OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}", "detail": "high"}},
                ]}],
                max_tokens=max_tokens,
            )
            text = (response.choices[0].message.content or "").strip()
            result.update(chars=len(text), finish=response.choices[0].finish_reason)
            if response.usage:
                result.update(in_tokens=response.usage.prompt_tokens, out_tokens=response.usage.completion_tokens)
            out_file = OUT / model.replace("/", "_") / f"{image.stem}.md"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(text, encoding="utf-8")
        except Exception as exc:  # unsupported vision input, 4xx/5xx, timeout...
            result["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    result["seconds"] = round(time.monotonic() - started, 1)
    price = PRICES.get(model)
    if price and result["in_tokens"] is not None:
        result["cost_usd"] = round((result["in_tokens"] * price[0] + (result["out_tokens"] or 0) * price[1]) / 1e6, 5)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


async def main() -> int:
    global OUT
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--models", nargs="*", default=list(PRICES))
    parser.add_argument("--images", nargs="*", type=Path, default=sorted((ROOT / "eval").glob("Dropped Image*.png")))
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--max-tokens", type=int, default=6000)
    args = parser.parse_args()
    OUT = args.out
    OUT.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    client = AsyncOpenAI(base_url=settings.llm_api_base_url, api_key=settings.llm_api_key, timeout=240, max_retries=0)
    sem = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(*(run_one(client, m, img, sem, args.max_tokens) for m in args.models for img in args.images))
    (OUT / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    await client.close()
    return 0


OUT: Path

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
