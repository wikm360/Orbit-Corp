import io
import shutil
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image, ImageDraw

from app.features.documents.ingestion import ocr as ocr_module
from app.features.documents.ingestion.image_orientation import (
    find_upright_rotation,
    parse_probe_answer,
    rotate_clockwise,
)


def _page_with_corner_marker() -> Image.Image:
    """Upright when the black square is in the top-left corner."""
    page = Image.new("RGB", (600, 800), "white")
    ImageDraw.Draw(page).rectangle((20, 20, 140, 100), fill="black")
    return page


def _is_upright(img: Image.Image) -> bool:
    w, h = img.size
    return img.getpixel((int(w * 0.05), int(h * 0.04))) == (0, 0, 0) and img.getpixel((w - 10, h - 10)) == (255, 255, 255)


def _model(wrong_direction: bool):
    """A fake vision model: always right about *whether* the page is upright, optionally wrong about the direction."""
    calls = []

    async def probe(img):
        calls.append(img.size)
        if _is_upright(img):
            return 0
        for degrees in (90, 270, 180):
            if _is_upright(rotate_clockwise(img, degrees)):
                return {90: 270, 270: 90}.get(degrees, degrees) if wrong_direction else degrees
        return None

    return probe, calls


def test_parse_probe_answer():
    assert parse_probe_answer('{"rotate_clockwise": 270}') == 270
    assert parse_probe_answer('```json\n{"rotate_clockwise":0}\n```') == 0
    assert parse_probe_answer("looks fine") is None
    assert parse_probe_answer('{"rotate_clockwise": 45}') is None


@pytest.mark.parametrize("wrong_direction", [False, True])
@pytest.mark.parametrize("needs_clockwise", [0, 90, 180, 270])
async def test_find_upright_rotation_even_when_the_model_names_the_wrong_direction(needs_clockwise, wrong_direction):
    upright = _page_with_corner_marker()
    scanned = upright.rotate(needs_clockwise, expand=True)  # rotating it back clockwise by the same amount restores it
    probe, calls = _model(wrong_direction)
    assert await find_upright_rotation(scanned, probe) == needs_clockwise
    if needs_clockwise == 0:
        assert len(calls) == 1  # an upright page costs one probe


async def test_probe_failures_never_rotate_and_never_raise():
    scanned = _page_with_corner_marker().rotate(90, expand=True)

    async def broken(img):
        raise RuntimeError("gateway down")

    async def no_answer(img):
        return None

    async def confused(img):  # claims "rotate 90" but never calls anything upright afterwards
        return 90

    assert await find_upright_rotation(scanned, broken) == 0
    assert await find_upright_rotation(scanned, no_answer) == 0
    assert await find_upright_rotation(scanned, confused) == 0


def _png(img: Image.Image) -> bytes:
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _settings(**overrides):
    values = dict(ocr_enabled=True, llm_api_key="k", llm_api_base_url="http://x/v1", llm_vision_model="m", ocr_max_tokens=100,
                  ocr_skip_blank_images=True, ocr_auto_orient=False, ocr_orient_method="model", ocr_orient_osd_min_confidence=2.0, ocr_orient_osd_upright_confidence=6.0, ocr_osd_concurrency=2, ocr_content_filter_retries=2, ocr_orient_min_dimension=600, ocr_deskew=False,
                  ocr_crop_margins=False, ocr_max_image_dimension=2560, ocr_jpeg_quality=95)
    values.update(overrides)
    return SimpleNamespace(**values)


def _client(*responses):
    client = MagicMock()
    client.close = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=list(responses))
    return client


def _reply(text, finish="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason=finish)])


async def test_blank_image_is_not_sent_to_the_model():
    client = _client()
    with patch.object(ocr_module, "AsyncOpenAI", return_value=client), patch.object(ocr_module, "get_settings", return_value=_settings()):
        assert await ocr_module.extract_text_from_image(_png(Image.new("RGB", (800, 1000), "white")), "png") == ""
    client.chat.completions.create.assert_not_called()


async def test_content_filtered_answer_is_retried():
    client = _client(_reply("", "content_filter"), _reply("", "content_filter"), _reply("متن نامه"))
    page = _page_with_corner_marker()
    with (
        patch.object(ocr_module, "AsyncOpenAI", return_value=client),
        patch.object(ocr_module, "get_settings", return_value=_settings()),
        patch.object(ocr_module.asyncio, "sleep", new=AsyncMock()),
    ):
        assert await ocr_module.extract_text_from_image(_png(page), "png") == "متن نامه"
    assert client.chat.completions.create.await_count == 3


async def test_rotated_page_is_turned_upright_before_ocr():
    scanned = _page_with_corner_marker().rotate(90, expand=True)  # needs 90 clockwise
    sent = []

    async def create(**kwargs):
        text = kwargs["messages"][0]["content"][0]["text"]
        image_url = kwargs["messages"][0]["content"][1]["image_url"]["url"]
        import base64
        import io

        img = Image.open(io.BytesIO(base64.b64decode(image_url.split(",", 1)[1]))).convert("RGB")
        if "rotate_clockwise" in text:  # the orientation probe
            for degrees in (0, 90, 180, 270):
                if _is_upright(rotate_clockwise(img, degrees)) and degrees == 0:
                    return _reply('{"rotate_clockwise": 0}')
            return _reply('{"rotate_clockwise": 90}')
        sent.append(_is_upright_jpeg(img))
        return _reply("متن")

    client = MagicMock()
    client.close = AsyncMock()
    client.chat.completions.create = create
    with (
        patch.object(ocr_module, "AsyncOpenAI", return_value=client),
        patch.object(ocr_module, "get_settings", return_value=_settings(ocr_auto_orient=True, ocr_orient_method="model")),
    ):
        assert await ocr_module.extract_text_from_image(_png(scanned), "png") == "متن"
    assert sent == [True]


def _is_upright_jpeg(img: Image.Image) -> bool:
    w, h = img.size
    r, g, b = img.getpixel((int(w * 0.05), int(h * 0.04)))
    return max(r, g, b) < 60  # JPEG: near-black rather than exactly black


def test_preprocess_signature_changes_with_the_flags_and_the_orient_method():
    with patch.object(ocr_module, "get_settings", return_value=_settings(ocr_auto_orient=True, ocr_orient_method="osd")):
        assert ocr_module.preprocess_signature() != _sig(ocr_orient_method="model")
        assert ocr_module.preprocess_signature() != _sig(ocr_orient_method="hybrid")


def _sig(**overrides):
    with patch.object(ocr_module, "get_settings", return_value=_settings(ocr_auto_orient=True, **overrides)):
        return ocr_module.preprocess_signature()


def test_preprocess_signature_changes_with_the_flags():
    with patch.object(ocr_module, "get_settings", return_value=_settings(ocr_auto_orient=True)):
        a = ocr_module.preprocess_signature()
    with patch.object(ocr_module, "get_settings", return_value=_settings(ocr_auto_orient=False)):
        b = ocr_module.preprocess_signature()
    with patch.object(ocr_module, "get_settings", return_value=_settings(ocr_auto_orient=True, ocr_deskew=True)):
        c = ocr_module.preprocess_signature()
    assert len({a, b, c}) == 3


async def test_content_filter_gives_up_after_its_retries_and_each_retry_changes_the_request():
    client = _client(*[_reply("", "content_filter")] * 3)
    with (
        patch.object(ocr_module, "AsyncOpenAI", return_value=client),
        patch.object(ocr_module, "get_settings", return_value=_settings()),  # 2 retries = 3 calls in all
        patch.object(ocr_module.asyncio, "sleep", new=AsyncMock()),
    ):
        assert await ocr_module.extract_text_from_image(_png(_page_with_corner_marker()), "png") == ""
    calls = client.chat.completions.create.await_args_list
    assert len(calls) == 3
    parts = [c.kwargs["messages"][0]["content"] for c in calls]
    images = [p[1]["image_url"]["url"] for p in parts]
    prompts = [p[0]["text"] for p in parts]
    assert len(set(images)) == 3 and len(set(prompts)) == 3  # never the same bytes / prompt twice
    assert all(prompts[i].startswith(ocr_module.SYSTEM_OCR_PROMPT) for i in range(3))

    # the varied page is still the same page, just a little bigger (border) and, from the 2nd retry, 2% scaled
    import base64

    sizes = [Image.open(io.BytesIO(base64.b64decode(u.split(",", 1)[1]))).size for u in images]
    assert sizes[1][0] > sizes[0][0] and sizes[1][1] > sizes[0][1]


async def test_the_number_of_content_filter_retries_is_configurable():
    client = _client(*[_reply("", "content_filter")] * 5, _reply("ok"))
    with (
        patch.object(ocr_module, "AsyncOpenAI", return_value=client),
        patch.object(ocr_module, "get_settings", return_value=_settings(ocr_content_filter_retries=5)),
        patch.object(ocr_module.asyncio, "sleep", new=AsyncMock()),
    ):
        assert await ocr_module.extract_text_from_image(_png(_page_with_corner_marker()), "png") == "ok"
    assert client.chat.completions.create.await_count == 6



# ---- Tesseract OSD and the OCR_ORIENT_METHOD decision table

from app.features.documents.ingestion.image_orientation import choose_rotation, detect_rotation_osd, parse_osd_output  # noqa: E402

OSD_SAMPLE = """Page number: 0
Orientation in degrees: 90
Rotate: 270
Orientation confidence: 6.32
Script: Arabic
Script confidence: 4.10
"""


def test_parse_osd_output():
    assert parse_osd_output(OSD_SAMPLE) == (270, 6.32)
    assert parse_osd_output("") == (None, 0.0)
    assert parse_osd_output("Too few characters. Skipping this page") == (None, 0.0)
    assert parse_osd_output("Rotate: 45\nOrientation confidence: 9.0") == (None, 0.0)


def _decide(method, osd_answer, probe, min_confidence=2.0, page=None, upright_confidence=6.0):
    page = page if page is not None else _page_with_corner_marker().rotate(90, expand=True)  # needs 90 clockwise
    osd_calls = []

    async def osd(img):
        osd_calls.append(1)
        if isinstance(osd_answer, Exception):
            raise osd_answer
        return osd_answer

    return (
        choose_rotation(
            page, method=method, probe=probe, osd=osd, min_confidence=min_confidence, upright_confidence=upright_confidence
        ),
        osd_calls,
    )


class _Probe:
    """Model stand-in that is right about whether a page is upright (see _model)."""

    def __init__(self, wrong_direction=False):
        self.calls = 0
        self._inner, _ = _model(wrong_direction)

    async def __call__(self, img):
        self.calls += 1
        return await self._inner(img)


async def test_model_method_never_runs_osd():
    probe = _Probe()
    result, osd_calls = _decide("model", (0, 20.0), probe)
    assert await result == 90 and osd_calls == []


async def test_osd_method_uses_osd_alone():
    probe = _Probe()
    result, _ = _decide("osd", (90, 7.0), probe)
    assert await result == 90 and probe.calls == 0
    result, _ = _decide("osd", (90, 1.0), probe)  # unsure: leave the page as it is, no model call
    assert await result == 0 and probe.calls == 0
    result, _ = _decide("osd", (None, 0.0), probe)
    assert await result == 0 and probe.calls == 0


async def test_hybrid_trusts_a_confident_upright_answer_without_calling_the_model():
    probe = _Probe()
    result, _ = _decide("hybrid", (0, 11.0), probe, page=_page_with_corner_marker())
    assert await result == 0 and probe.calls == 0


async def test_hybrid_double_checks_a_weak_upright_answer_with_the_model():
    """A sideways drawing was called upright by OSD at confidence 2.6: below the upright bar the model decides."""
    sideways = _page_with_corner_marker().rotate(90, expand=True)  # needs 90 clockwise
    probe = _Probe()
    result, _ = _decide("hybrid", (0, 2.6), probe, page=sideways)
    assert await result == 90 and probe.calls >= 1
    # a really upright page with a weak OSD answer costs one probe and stays as it is
    probe = _Probe()
    result, _ = _decide("hybrid", (0, 2.6), probe, page=_page_with_corner_marker())
    assert await result == 0 and probe.calls == 1
    # osd-only mode has no model to ask: it keeps its answer
    result, _ = _decide("osd", (0, 2.6), _Probe(), page=sideways)
    assert await result == 0


async def test_hybrid_confirms_a_proposed_rotation_with_one_model_call():
    probe = _Probe()
    result, _ = _decide("hybrid", (90, 6.0), probe)
    assert await result == 90 and probe.calls == 1


async def test_hybrid_does_not_rotate_an_upright_page_that_osd_wrongly_calls_sideways():
    """The risky mistake (an upright page called rotated): the model disagrees, so the page is left alone."""
    probe = _Probe()
    result, _ = _decide("hybrid", (180, 4.6), probe, page=_page_with_corner_marker())
    assert await result == 0


async def test_hybrid_falls_back_to_the_model_when_osd_is_unsure_or_broken():
    for osd_answer in [(90, 1.0), (None, 0.0), RuntimeError("boom")]:
        probe = _Probe(wrong_direction=True)  # the model alone still finds the rotation through its confirmation step
        result, _ = _decide("hybrid", osd_answer, probe)
        assert await result == 90


async def test_hybrid_asks_the_model_when_it_disagrees_with_a_confident_osd_rotation():
    probe = _Probe()
    result, _ = _decide("hybrid", (270, 8.0), probe)  # wrong direction from OSD: the model finds the real one
    assert await result == 90


def test_detect_rotation_osd_without_tesseract_returns_nothing(monkeypatch):
    from app.features.documents.ingestion import image_orientation as module

    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    monkeypatch.setattr(module, "_osd_missing_logged", False)
    import asyncio

    assert asyncio.run(detect_rotation_osd(Image.new("RGB", (100, 100), "white"))) == (None, 0.0)


def _text_page() -> Image.Image:
    from PIL import ImageFont

    page = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(page)
    font = ImageFont.load_default(size=34)
    words = "Contract amount payable to the contractor shall be adjusted according to the approved quantities".split()
    for row in range(32):
        draw.text((120, 120 + row * 46), " ".join(words[(row + i) % len(words)] for i in range(10)), fill="black", font=font)
    return page


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
@pytest.mark.parametrize("needs_clockwise", [0, 90, 180, 270])
async def test_osd_finds_the_rotation_of_a_real_text_page(needs_clockwise):
    scanned = _text_page().rotate(needs_clockwise, expand=True, fillcolor=(255, 255, 255))
    degrees, confidence = await detect_rotation_osd(scanned)
    assert degrees == needs_clockwise and confidence > 2.0


def _orientation_logs(caplog):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith("OCR orientation")]


async def test_decision_path_is_logged_for_every_method(caplog):
    import logging

    caplog.set_level(logging.INFO, logger="app.features.documents.ingestion.image_orientation")
    sideways = _page_with_corner_marker().rotate(90, expand=True)
    upright = _page_with_corner_marker()

    await _decide("hybrid", (0, 11.4), _Probe(), page=upright)[0]
    await _decide("hybrid", (90, 6.3), _Probe())[0]
    await _decide("hybrid", (90, 1.0), _Probe(wrong_direction=True))[0]
    await _decide("hybrid", (None, 0.0), _Probe())[0]
    await _decide("osd", (90, 1.0), _Probe())[0]
    await _decide("model", (0, 20.0), _Probe())[0]
    await _decide("hybrid", (270, 8.0), _Probe(), page=sideways)[0]
    lines = _orientation_logs(caplog)

    assert len(lines) == 7
    assert "[hybrid]" in lines[0] and "osd: 0 (confidence 11.4)" in lines[0] and "no model call" in lines[0] and "keep as is" in lines[0]
    assert "osd: 90 (confidence 6.3)" in lines[1] and "model confirmed" in lines[1] and "rotate 90" in lines[1]
    assert "below 2 = unsure" in lines[2] and "falling back to the model" in lines[2] and "model: says rotated" in lines[2]
    assert "osd: no answer" in lines[3]
    assert "[osd]" in lines[4] and "left as is" in lines[4] and "model:" not in lines[4]
    assert "[model]" in lines[5] and "model: " in lines[5] and "osd" not in lines[5]
    assert "model disagreed" in lines[6]


async def test_a_known_rotation_skips_detection_and_is_reported():
    scanned = _page_with_corner_marker().rotate(90, expand=True)  # needs 90 clockwise
    settings = _settings(ocr_auto_orient=True, ocr_orient_method="hybrid")
    detect = AsyncMock(side_effect=AssertionError("detection must not run when the rotation is known"))
    with patch.object(ocr_module, "get_settings", return_value=settings), patch.object(ocr_module, "choose_rotation", new=detect):
        report: dict = {}
        data, _ = await ocr_module.prepare_image_for_ocr(_png(scanned), rotation=90, report=report)
        assert report == {"rotation": 90}
        assert _is_upright_jpeg(Image.open(io.BytesIO(data)).convert("RGB"))
        report = {}
        await ocr_module.prepare_image_for_ocr(_png(_page_with_corner_marker()), rotation=0, report=report)  # 0 is known too
        assert report == {"rotation": 0}


async def test_detected_rotation_is_reported_and_unknown_when_detection_does_not_run():
    scanned = _page_with_corner_marker().rotate(90, expand=True)
    with (
        patch.object(ocr_module, "get_settings", return_value=_settings(ocr_auto_orient=True)),
        patch.object(ocr_module, "choose_rotation", new=AsyncMock(return_value=90)),
    ):
        report: dict = {}
        await ocr_module.prepare_image_for_ocr(_png(scanned), report=report)
        assert report == {"rotation": 90}
    with patch.object(ocr_module, "get_settings", return_value=_settings(ocr_auto_orient=False)):
        report = {}
        await ocr_module.prepare_image_for_ocr(_png(scanned), report=report)
        assert report == {}  # not determined: nothing is stored, so a later view detects it


async def test_the_hint_is_verified_alone_first_and_the_other_rotations_only_if_it_fails():
    for wrong_direction, expected_calls in [(False, 2), (True, 4)]:
        probe = _Probe(wrong_direction=wrong_direction)
        sideways = _page_with_corner_marker().rotate(90, expand=True)  # needs 90 clockwise
        assert await find_upright_rotation(sideways, probe) == 90
        assert probe.calls == expected_calls  # right hint: probe + 1 check; wrong hint: probe + 1 check + 2 others
    probe = _Probe()
    assert await find_upright_rotation(_page_with_corner_marker(), probe) == 0 and probe.calls == 1
