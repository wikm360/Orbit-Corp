from app.features.documents.ingestion.parser import parse_document


def _write(tmp_path, name: str, data: bytes):
    path = tmp_path / name
    path.write_bytes(data)
    return path


async def test_plain_utf8_txt_parses_unchanged(tmp_path):
    text = "(.venv) E:\\wikm\\STT>python transcribe.py\nخروجی: تست فارسی\n"
    path = _write(tmp_path, "note.txt", text.encode("utf-8"))

    result = parse_document(str(path))

    assert result == text
    assert "\x00" not in result


async def test_utf16_le_with_bom_is_decoded_correctly(tmp_path):
    """Reproduces the bug report: a Windows-originated transcript (e.g. from
    PowerShell's Start-Transcript) saved as UTF-16LE. A naive
    `read_text(encoding="utf-8")` doesn't raise on this - every ASCII byte
    followed by a NUL byte is individually valid UTF-8 - so it silently
    corrupts the text with a literal NUL after every character, which
    Postgres then rejects outright on insert."""
    text = "(.venv) E:\\wikm\\STT\\STT>python transcribe.py\nمتن فارسی تستی\n"
    path = _write(tmp_path, "transcript.txt", text.encode("utf-16"))  # adds a BOM

    result = parse_document(str(path))

    assert result == text
    assert "\x00" not in result


async def test_utf16_le_without_bom_is_still_detected_by_heuristic(tmp_path):
    text = "plain ascii transcript content with no special characters at all"
    path = _write(tmp_path, "no-bom.txt", text.encode("utf-16-le"))

    result = parse_document(str(path))

    assert result == text
    assert "\x00" not in result


async def test_utf8_with_bom_strips_the_bom(tmp_path):
    text = "hello world"
    path = _write(tmp_path, "bom.txt", b"\xef\xbb\xbf" + text.encode("utf-8"))

    result = parse_document(str(path))

    assert result == text
