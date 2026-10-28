"""Converts legacy/odd office formats (.xls, .doc, .ppt, .rtf, .odt, ...) to their modern OOXML twin with LibreOffice.

Each call runs its own headless `soffice` with a throw-away user profile: two conversions never share the profile lock,
and a hung/crashed converter cannot poison the next file. The converted copy lives in a temp dir that disappears when
the `with` block ends."""

import logging
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)

# legacy suffix -> (modern suffix, LibreOffice filter name)
CONVERTIBLE_EXTENSIONS: dict[str, tuple[str, str]] = {
    ".xls": (".xlsx", "xlsx:Calc MS Excel 2007 XML"),
    ".xlsm": (".xlsx", "xlsx:Calc MS Excel 2007 XML"),
    ".ods": (".xlsx", "xlsx:Calc MS Excel 2007 XML"),
    ".doc": (".docx", "docx:MS Word 2007 XML"),
    ".rtf": (".docx", "docx:MS Word 2007 XML"),
    ".odt": (".docx", "docx:MS Word 2007 XML"),
    ".ppt": (".pptx", "pptx:Impress MS PowerPoint 2007 XML"),
    ".odp": (".pptx", "pptx:Impress MS PowerPoint 2007 XML"),
}


def _looks_like_office_file(path: Path) -> bool:
    """LibreOffice "converts" any garbage by importing it as text, which would embed noise. Accept only real containers:
    OLE2 (.xls/.doc/.ppt), ZIP (.ods/.odt/.odp/.xlsm), RTF, or the HTML/XML some tools export under an .xls/.doc name."""
    with path.open("rb") as handle:
        head = handle.read(512).lstrip()
    return head.startswith((b"\xd0\xcf\x11\xe0", b"PK\x03\x04", b"{\\rtf", b"<"))


@contextmanager
def converted_copy(file_path: str) -> Iterator[str]:
    """Yields the path of a modern-format copy of `file_path` (see `CONVERTIBLE_EXTENSIONS`)."""
    source = Path(file_path)
    target_suffix, convert_to = CONVERTIBLE_EXTENSIONS[source.suffix.lower()]
    timeout = get_settings().office_convert_timeout_seconds
    if not _looks_like_office_file(source):
        raise BadRequestError(f"This {source.suffix} file is damaged or is not really a {source.suffix} document.")

    with tempfile.TemporaryDirectory(prefix="convert-") as work:
        work_dir = Path(work)
        out_dir = work_dir / "out"
        out_dir.mkdir()
        # Symlink under a neutral ASCII name: soffice mishandles some non-ASCII/odd paths and the output is named after it.
        staged = work_dir / f"input{source.suffix.lower()}"
        staged.symlink_to(source.resolve())
        cmd = [
            "soffice",
            f"-env:UserInstallation=file://{work_dir / 'profile'}",
            "--headless",
            "--norestore",
            "--nolockcheck",
            "--convert-to",
            convert_to,
            "--outdir",
            str(out_dir),
            str(staged),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=work, text=True, errors="replace")
        except FileNotFoundError as exc:
            raise BadRequestError("LibreOffice is not installed on this server, so this file type cannot be read.") from exc
        except subprocess.TimeoutExpired as exc:
            raise BadRequestError(f"Converting {source.suffix} to {target_suffix} took longer than {timeout}s.") from exc

        produced = out_dir / f"input{target_suffix}"
        if result.returncode != 0 or not produced.exists() or produced.stat().st_size == 0:
            logger.warning("soffice failed for %s (rc=%s): %s", file_path, result.returncode, (result.stderr or result.stdout)[:500])
            raise BadRequestError(f"Could not convert this {source.suffix} file (damaged, password-protected or unsupported).")
        yield str(produced)
