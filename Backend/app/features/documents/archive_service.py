"""Archive (.zip/.rar/.7z) uploads: stored, then unpacked by the worker into the folder they were uploaded to.

Every member becomes an ordinary document queued for ingestion, so a bad member never affects the others. Extraction
is defensive: member paths can't escape the target (zip-slip), symlinks are ignored, and the number of files, their
total unpacked size and the nesting depth are capped (zip bombs). Junk (CAD fonts/backups, OS metadata) is skipped
and counted, not imported.
"""
import asyncio
import logging
import os
import shutil
import stat
import subprocess
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException
from sqlalchemy import func

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.exceptions import BadRequestError
from app.features.documents import service
from app.features.documents.folder_service import (
    MAX_DOCUMENT_NAME_LENGTH,
    ensure_folder_path,
    get_folder,
)
from app.features.documents.models import ArchiveImport, ArchiveImportStatus
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()

ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}

# Never worth importing: CAD fonts/lisp/lock files, backups, logs, temp files, OS metadata. (Unsupported-but-real files
# such as .dwg are NOT here: they are kept, shown as unsupported, and can be processed once a parser exists.)
_JUNK_SUFFIXES = {".shx", ".lsp", ".bak", ".log", ".tmp", ".dwl", ".dwl2", ".ds_store"}
_JUNK_NAMES = {"thumbs.db", "desktop.ini", ".ds_store"}
_JUNK_DIRS = {"__macosx"}

_MAX_RECORDED_FAILURES = 200
_SEVENZIP_TIMEOUT_SECONDS = 1800
_PROGRESS_EVERY = 20


def _scratch_dir() -> str:
    """Where archives are unpacked: the uploads volume, not /tmp (a tmpfs in production, i.e. RAM, where a multi-GB
    archive would exhaust the container's memory limit)."""
    path = Path(settings.upload_dir) / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def is_archive(filename: str | None) -> bool:
    return Path(filename or "").suffix.lower() in ARCHIVE_EXTENSIONS


class ArchiveError(Exception):
    """The archive as a whole can't be imported (corrupt, encrypted, over a limit)."""


@dataclass(frozen=True)
class Limits:
    max_files: int
    max_total_bytes: int
    max_depth: int

    @classmethod
    def from_settings(cls) -> "Limits":
        return cls(
            max_files=settings.archive_max_files,
            max_total_bytes=settings.archive_max_total_size_mb * 1024 * 1024,
            max_depth=settings.archive_max_depth,
        )


def is_junk(parts: list[str]) -> bool:
    if any(p.lower() in _JUNK_DIRS for p in parts[:-1]):
        return True
    name = parts[-1]
    lower = name.lower()
    return (
        lower in _JUNK_NAMES
        or lower.startswith("~$")  # Office lock file
        or lower.startswith("._")  # macOS resource fork
        or Path(lower).suffix in _JUNK_SUFFIXES
    )


def _decode_zip_name(info: zipfile.ZipInfo) -> str:
    """zipfile decodes names without the UTF-8 flag as cp437. Windows tools on a Persian system write cp1256/cp720
    bytes there instead, so re-read the raw bytes: valid UTF-8 first, else cp1256."""
    if info.flag_bits & 0x800:
        return info.filename
    raw = info.filename.encode("cp437", errors="replace")
    for encoding in ("utf-8", "cp1256"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return info.filename


def _safe_parts(name: str) -> list[str] | None:
    """Path segments of a member name, or None when it is unsafe (absolute, drive letter, `..`)."""
    normalized = name.replace("\\", "/").replace("\x00", "")
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        return None
    parts = [p for p in normalized.split("/") if p and p != "."]
    if any(p == ".." for p in parts) or not parts:
        return None
    return parts


# ---------------------------------------------------------------------------
# Extraction to a scratch directory (sync; run in a thread)
# ---------------------------------------------------------------------------


@dataclass
class ExtractionReport:
    total: int = 0
    skipped: int = 0
    failures: list[dict] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.failures = []

    def fail(self, path: str, error: str) -> None:
        if len(self.failures) < _MAX_RECORDED_FAILURES:
            self.failures.append({"path": path, "error": error})


def _extract_zip(archive: Path, dest: Path, limits: Limits, report: ExtractionReport) -> None:
    try:
        zf = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise ArchiveError("The file is not a valid zip archive") from exc
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > limits.max_files:
            raise ArchiveError(f"The archive holds more than {limits.max_files} files")
        if sum(i.file_size for i in infos) > limits.max_total_bytes:
            raise ArchiveError("The archive expands to more than the allowed total size")
        if any(i.flag_bits & 0x1 for i in infos):
            raise ArchiveError("The archive is password-protected")

        written = 0
        for info in infos:
            report.total += 1
            name = _decode_zip_name(info)
            parts = _safe_parts(name)
            if parts is None:
                report.fail(name, "Unsafe path in archive")
                continue
            if stat.S_ISLNK(info.external_attr >> 16):
                report.skipped += 1  # symlinks are never followed
                continue
            if is_junk(parts):
                report.skipped += 1
                continue
            target = dest.joinpath(*parts)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    # Enforce the cap on bytes actually produced: the declared size in the header can lie.
                    remaining = limits.max_total_bytes - written
                    copied = 0
                    while chunk := src.read(1024 * 1024):
                        copied += len(chunk)
                        if copied > remaining:
                            raise ArchiveError("The archive expands to more than the allowed total size")
                        out.write(chunk)
                    written += copied
            except ArchiveError:
                raise
            except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
                report.fail(name, f"Could not extract: {exc}")


def _list_7z(archive: Path) -> list[dict]:
    """Entries of an archive as reported by `7z l -slt` (one dict per entry)."""
    proc = subprocess.run(
        ["7z", "l", "-slt", "-ba", "-p-", "-sccUTF-8", str(archive)],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=_SEVENZIP_TIMEOUT_SECONDS,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        lowered = (out + proc.stderr.decode("utf-8", errors="replace")).lower()
        if "password" in lowered or "encrypted" in lowered:
            raise ArchiveError("The archive is password-protected")
        raise ArchiveError("The file is not a valid or supported archive")
    entries: list[dict] = []
    for block in out.split("\n\n"):
        entry: dict[str, str] = {}
        for line in block.splitlines():
            if " = " in line:
                key, _, value = line.partition(" = ")
                entry[key.strip()] = value.strip()
        if "Path" in entry:
            entries.append(entry)
    return entries


def _run_cli_extract(archive: Path, dest: Path) -> None:
    """Unpacks with the best installed tool. `.rar` prefers `unrar` (Debian's 7-Zip is built without the RAR codec
    and silently writes empty files for it - caught by the size check in `_extract_7z`); everything else uses `7z`."""
    if archive.suffix.lower() == ".rar" and shutil.which("unrar"):
        proc = subprocess.run(
            ["unrar", "x", "-y", "-idq", "-p-", "-o+", str(archive), f"{dest}{os.sep}"],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=_SEVENZIP_TIMEOUT_SECONDS,
        )
        if proc.returncode != 0:
            raise ArchiveError("The archive could not be extracted (it may be corrupt or password-protected)")
        return
    proc = subprocess.run(
        ["7z", "x", "-y", "-bso0", "-bsp0", "-p-", "-sccUTF-8", f"-o{dest}", str(archive)],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=_SEVENZIP_TIMEOUT_SECONDS,
    )
    if proc.returncode not in (0, 1):  # 1 = warnings
        raise ArchiveError("The archive could not be extracted (it may be corrupt)")


def _extract_7z(archive: Path, dest: Path, limits: Limits, report: ExtractionReport) -> None:
    """.rar/.7z through external tools: validate the listing first, extract, then re-validate what landed on disk."""
    if shutil.which("7z") is None:
        raise ArchiveError("The server cannot unpack this archive type (7z is not installed)")
    entries = [e for e in _list_7z(archive) if e.get("Folder") != "+"]
    if len(entries) > limits.max_files:
        raise ArchiveError(f"The archive holds more than {limits.max_files} files")
    if sum(int(e.get("Size") or 0) for e in entries) > limits.max_total_bytes:
        raise ArchiveError("The archive expands to more than the allowed total size")
    if any(e.get("Encrypted") == "+" for e in entries):
        raise ArchiveError("The archive is password-protected")
    if any(_safe_parts(e["Path"]) is None for e in entries):
        raise ArchiveError("The archive contains unsafe paths")
    declared = {"/".join(_safe_parts(e["Path"]) or []): int(e.get("Size") or 0) for e in entries}

    _run_cli_extract(archive, dest)

    total = 0
    dest_real = os.path.realpath(dest)
    for root, _dirs, files in os.walk(dest, followlinks=False):
        for name in files:
            path = Path(root, name)
            report.total += 1
            rel = path.relative_to(dest).parts
            if path.is_symlink() or not os.path.realpath(path).startswith(dest_real + os.sep):
                path.unlink(missing_ok=True)
                report.skipped += 1
                continue
            if is_junk(list(rel)):
                path.unlink(missing_ok=True)
                report.skipped += 1
                continue
            size = path.stat().st_size
            if declared.get("/".join(rel), size) != size:
                raise ArchiveError("The archive uses a compression method this server cannot unpack")
            total += size
            if total > limits.max_total_bytes:
                raise ArchiveError("The archive expands to more than the allowed total size")


def _extract(archive: Path, dest: Path, limits: Limits) -> ExtractionReport:
    report = ExtractionReport()
    if archive.suffix.lower() == ".zip":
        _extract_zip(archive, dest, limits, report)
    else:
        _extract_7z(archive, dest, limits, report)
    return report


# ---------------------------------------------------------------------------
# Upload + queueing
# ---------------------------------------------------------------------------


class _StreamingUpload(Protocol):
    filename: str | None

    async def read(self, size: int = -1) -> bytes: ...


async def create_archive_import(
    db: AsyncSession,
    upload: _StreamingUpload,
    *,
    project_id: uuid.UUID,
    folder_id: uuid.UUID | None,
    uploaded_by: uuid.UUID,
) -> ArchiveImport:
    """Streams the archive to disk (never fully in memory) and queues its extraction."""
    filename = upload.filename or "archive"
    if len(filename) > service._MAX_FILENAME_LENGTH:
        raise BadRequestError("File name is too long")
    if folder_id is not None:
        await get_folder(db, project_id, folder_id)

    max_bytes = settings.max_archive_size_mb * 1024 * 1024
    target_dir = Path(settings.upload_dir) / "archives"
    target_dir.mkdir(parents=True, exist_ok=True)
    stored = target_dir / f"{uuid.uuid4()}{Path(filename).suffix.lower()}"
    size = 0
    try:
        with open(stored, "wb") as out:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise BadRequestError("Archive exceeds the maximum allowed archive size")
                out.write(chunk)
        if size == 0:
            raise BadRequestError("File is empty")
    except BaseException:
        stored.unlink(missing_ok=True)
        raise

    archive = ArchiveImport(
        project_id=project_id,
        folder_id=folder_id,
        filename=filename,
        file_path=str(stored),
        status=ArchiveImportStatus.EXTRACTING,
        uploaded_by=uploaded_by,
    )
    db.add(archive)
    await db.commit()
    await db.refresh(archive)
    service._queue.enqueue(
        "app.features.documents.archive_service.run_archive_import_sync",
        archive.id,
        job_timeout=settings.archive_job_timeout_seconds,
    )
    return archive


# ---------------------------------------------------------------------------
# Worker side
# ---------------------------------------------------------------------------


class _Importer:
    """Turns an extracted directory tree into folders + documents under one archive's target folder.

    Counters live here, not on the ORM row: a failed member rolls the session back, which expires every loaded
    instance, so progress is written by re-loading the row (`_save`)."""

    def __init__(self, db: AsyncSession, archive: ArchiveImport, limits: Limits):
        self.db = db
        self.archive_id = archive.id
        self.project_id = archive.project_id
        self.uploaded_by = archive.uploaded_by
        self.limits = limits
        self.folder_cache: dict = {}
        self.total = 0
        self.skipped = 0
        self.imported = 0
        self.failures: list[dict] = []
        self._since_save = 0

    def add_report(self, report: ExtractionReport) -> None:
        self.total += report.total
        self.skipped += report.skipped
        for failure in report.failures:
            self._fail(failure["path"], failure["error"])

    def _fail(self, path: str, error: str) -> None:
        if len(self.failures) < _MAX_RECORDED_FAILURES:
            self.failures.append({"path": path, "error": error[:300]})

    async def save(self) -> None:
        archive = await self.db.get(ArchiveImport, self.archive_id)
        archive.total_files = self.total
        archive.skipped_files = self.skipped
        archive.imported_files = self.imported
        archive.failed_files = list(self.failures)
        await self.db.commit()

    async def import_tree(self, root: Path, base_folder_id: uuid.UUID | None, depth: int) -> None:
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
            rel = list(path.relative_to(root).parts)
            display = "/".join(rel)
            try:
                if is_archive(path.name):
                    if depth >= self.limits.max_depth:
                        self._fail(display, "Archive nested too deeply")
                    else:
                        await self._import_nested(path, rel, base_folder_id, depth)
                    continue

                size = path.stat().st_size
                if size == 0:
                    raise BadRequestError("File is empty")
                if size > max_bytes:
                    raise BadRequestError("File exceeds the maximum allowed upload size")
                folder_id = await ensure_folder_path(
                    self.db, self.project_id, base_folder_id, rel[:-1], self.uploaded_by, self.folder_cache
                )
                await service._create_document(
                    self.db,
                    filename=rel[-1][:MAX_DOCUMENT_NAME_LENGTH],
                    content_type="application/octet-stream",
                    file_bytes=await asyncio.to_thread(path.read_bytes),
                    uploaded_by=self.uploaded_by,
                    project_id=self.project_id,
                    conversation_id=None,
                    folder_id=folder_id,
                    keep_unsupported=True,
                )
                self.imported += 1
            except Exception as exc:  # noqa: BLE001 - one bad member never stops the rest
                await self.db.rollback()
                detail = str(exc.detail) if isinstance(exc, HTTPException) else f"{type(exc).__name__}: {exc}"
                logger.warning("Archive %s: member %s failed: %s", self.archive_id, display, detail)
                self._fail(display, detail)
            finally:
                self._since_save += 1
                if self._since_save >= _PROGRESS_EVERY:
                    self._since_save = 0
                    await self.save()

    async def _import_nested(self, path: Path, rel: list[str], base_folder_id: uuid.UUID | None, depth: int) -> None:
        """An archive inside the archive is unpacked into a sub-folder named after it."""
        stem_parts = [*rel[:-1], Path(rel[-1]).stem or rel[-1]]
        nested_folder = await ensure_folder_path(
            self.db, self.project_id, base_folder_id, stem_parts, self.uploaded_by, self.folder_cache
        )
        with tempfile.TemporaryDirectory(prefix="nested-archive-", dir=_scratch_dir()) as tmp:
            self.add_report(await asyncio.to_thread(_extract, path, Path(tmp), self.limits))
            await self.import_tree(Path(tmp), nested_folder, depth + 1)


async def run_archive_import(archive_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        archive = await db.get(ArchiveImport, archive_id)
        if archive is None or archive.status != ArchiveImportStatus.EXTRACTING or not archive.file_path:
            return
        archive_path = Path(archive.file_path)
        importer = _Importer(db, archive, Limits.from_settings())
        status, error = ArchiveImportStatus.DONE, None
        try:
            with tempfile.TemporaryDirectory(prefix="archive-", dir=_scratch_dir()) as tmp:
                importer.add_report(await asyncio.to_thread(_extract, archive_path, Path(tmp), importer.limits))
                await importer.save()
                await importer.import_tree(Path(tmp), archive.folder_id, 0)
        except ArchiveError as exc:
            status, error = ArchiveImportStatus.FAILED, str(exc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Archive import %s failed", archive_id)
            status, error = ArchiveImportStatus.FAILED, f"Unexpected error: {type(exc).__name__}"
        finally:
            archive_path.unlink(missing_ok=True)

        await db.rollback()
        await importer.save()
        archive = await db.get(ArchiveImport, archive_id)
        archive.status = status
        archive.error_message = error
        archive.file_path = None
        archive.finished_at = func.now()
        await db.commit()


def run_archive_import_sync(archive_id: uuid.UUID) -> None:
    """Sync entry point for the RQ worker."""
    asyncio.run(run_archive_import(archive_id))
