"""Archive uploads (.zip/.7z): stored, unpacked by the worker into the target folder, one document per member."""
import io
import shutil
import stat
import subprocess
import uuid
import zipfile
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.features.documents import archive_service, service
from app.features.documents.models import ArchiveImport, ArchiveImportStatus
from tests.features.documents.test_file_manager import _folder, _leader_with_project, _listing


@pytest.fixture(autouse=True)
def _isolated_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path / "uploads"))
    queued: list = []
    monkeypatch.setattr(service._queue, "enqueue", lambda fn, *a, **kw: queued.append((fn, a)))
    return queued


@pytest.fixture
def queued(_isolated_storage):
    return _isolated_storage


def _zip(members: dict[str, bytes], *, symlinks: dict[str, str] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
        for name, target in (symlinks or {}).items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, target)
    return buf.getvalue()


async def _upload_archive(client, headers, pid, name: str, data: bytes, folder_id=None) -> dict:
    response = await client.post(
        f"/api/v1/projects/{pid}/documents",
        files={"file": (name, data, "application/octet-stream")},
        data={"folder_id": folder_id} if folder_id else None,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["archive"]


async def _run(archive: dict) -> dict:
    await archive_service.run_archive_import(uuid.UUID(archive["id"]))
    return archive


async def _archive_state(client, headers, pid, folder_id=None) -> dict:
    archives = (await _listing(client, headers, pid, folder_id))["archives"]
    assert len(archives) == 1
    return archives[0]


async def _tree(client, headers, pid, folder_id=None, prefix="") -> dict[str, str]:
    """{'dir/file.ext': status} for everything below a folder."""
    listing = await _listing(client, headers, pid, folder_id)
    out = {prefix + d["filename"]: d["status"] for d in listing["documents"]}
    for entry in listing["folders"]:
        folder = entry["folder"]
        out.update(await _tree(client, headers, pid, folder["id"], f"{prefix}{folder['name']}/"))
    return out


async def test_zip_upload_is_queued_and_extracted_into_the_upload_folder(client, queued, tmp_path):
    leader, pid, _, _ = await _leader_with_project(client, "zip")
    target = await _folder(client, leader, pid, "Incoming")
    data = _zip(
        {
            "readme.txt": b"top level",
            "reports/2026/q1.txt": b"q1",
            "reports/q2.txt": b"q2",
            "plan.dwg": b"AC1027",  # no parser: kept, shown unsupported
            "fonts/arial.shx": b"junk",  # CAD junk: skipped
            "__MACOSX/._readme.txt": b"junk",
            "~$draft.docx": b"junk",
            "Thumbs.db": b"junk",
            "backup.bak": b"junk",
        }
    )

    archive = await _upload_archive(client, leader, pid, "bundle.zip", data, folder_id=target["id"])
    assert archive["status"] == "extracting" and archive["folder_id"] == target["id"]
    assert [fn for fn, _ in queued] == ["app.features.documents.archive_service.run_archive_import_sync"]
    stored = list((tmp_path / "uploads" / "archives").glob("*.zip"))
    assert len(stored) == 1

    await _run(archive)

    # only the real files were imported, below the folder the archive was uploaded to
    assert await _tree(client, leader, pid, target["id"]) == {
        "readme.txt": "processing",
        "reports/2026/q1.txt": "processing",
        "reports/q2.txt": "processing",
        "plan.dwg": "unsupported",
    }
    assert (await _listing(client, leader, pid))["documents"] == []
    state = await _archive_state(client, leader, pid, target["id"])
    assert state["status"] == "done"
    assert (state["total_files"], state["imported_files"], state["skipped_files"]) == (9, 4, 5)
    assert state["failed_files"] == [] and state["finished_at"] is not None
    # the archive itself is not kept on disk, and every supported member got its own ingestion job
    assert not stored[0].exists()
    assert sum(1 for fn, _ in queued if fn.endswith("run_ingestion_pipeline_sync")) == 3


async def test_one_bad_member_does_not_affect_the_others(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_size_mb", 1)
    leader, pid, _, _ = await _leader_with_project(client, "badmember")
    data = _zip({"ok.txt": b"fine", "huge.txt": b"x" * (1024 * 1024 + 1), "empty.txt": b"", "also-ok.txt": b"fine too"})
    archive = await _run(await _upload_archive(client, leader, pid, "mixed.zip", data))

    assert await _tree(client, leader, pid) == {"ok.txt": "processing", "also-ok.txt": "processing"}
    state = await _archive_state(client, leader, pid)
    assert state["status"] == "done" and state["imported_files"] == 2
    assert {f["path"]: f["error"] for f in state["failed_files"]} == {
        "huge.txt": "File exceeds the maximum allowed upload size",
        "empty.txt": "File is empty",
    }


async def test_zip_slip_and_symlink_members_never_escape_or_import(client, tmp_path):
    leader, pid, _, _ = await _leader_with_project(client, "slip")
    data = _zip({"ok.txt": b"ok", "../evil.txt": b"evil", "/abs/evil2.txt": b"evil", "a/../../evil3.txt": b"evil"}, symlinks={"link.txt": "/etc/passwd"})
    archive = await _run(await _upload_archive(client, leader, pid, "slip.zip", data))

    assert await _tree(client, leader, pid) == {"ok.txt": "processing"}
    state = await _archive_state(client, leader, pid)
    assert state["status"] == "done"
    assert {f["path"] for f in state["failed_files"]} == {"../evil.txt", "/abs/evil2.txt", "a/../../evil3.txt"}
    assert state["skipped_files"] == 1  # the symlink
    assert not (tmp_path / "evil.txt").exists() and not (tmp_path.parent / "evil.txt").exists()


async def test_persian_names_in_a_legacy_cp1256_zip_are_decoded(client):
    leader, pid, _, _ = await _leader_with_project(client, "fa")
    folder_name, file_name = "گزارش پروژه", "نقشه.txt"
    raw_dir, raw_file = f"{folder_name}/".encode("cp1256"), file_name.encode("cp1256")
    data = _zip({"X" * len(raw_dir) + "X" * len(raw_file): b"content"}).replace(b"X" * (len(raw_dir) + len(raw_file)), raw_dir + raw_file)
    # sanity: this really is a name without the UTF-8 flag that zipfile mis-decodes
    assert zipfile.ZipFile(io.BytesIO(data)).infolist()[0].flag_bits & 0x800 == 0

    await _run(await _upload_archive(client, leader, pid, "fa.zip", data))
    assert await _tree(client, leader, pid) == {f"{folder_name}/{file_name}": "processing"}


async def test_utf8_names_are_kept_with_or_without_the_utf8_flag(client):
    leader, pid, _, _ = await _leader_with_project(client, "utf8")
    flagged, unflagged = "پیش بینی.txt", "احجام کل.txt"
    raw = unflagged.encode("utf-8")
    data = _zip({flagged: b"one", "X" * len(raw): b"two"}).replace(b"X" * len(raw), raw)
    flags = [i.flag_bits & 0x800 for i in zipfile.ZipFile(io.BytesIO(data)).infolist()]
    assert flags == [0x800, 0]  # a UTF-8 name some tools write without the flag must not be mis-read as cp437/cp1256
    await _run(await _upload_archive(client, leader, pid, "u.zip", data))
    assert sorted(await _tree(client, leader, pid)) == sorted([flagged, unflagged])


@pytest.mark.parametrize(
    ("limit", "value", "members", "message"),
    [
        ("archive_max_files", 2, {"a.txt": b"a", "b.txt": b"b", "c.txt": b"c"}, "more than 2 files"),
        ("archive_max_total_size_mb", 1, {"zeros.txt": b"\0" * (2 * 1024 * 1024)}, "allowed total size"),
    ],
)
async def test_archive_over_a_limit_fails_as_a_whole_and_imports_nothing(client, monkeypatch, limit, value, members, message):
    monkeypatch.setattr(get_settings(), limit, value)
    leader, pid, _, _ = await _leader_with_project(client, f"limit-{limit}")
    await _run(await _upload_archive(client, leader, pid, "big.zip", _zip(members)))

    state = await _archive_state(client, leader, pid)
    assert state["status"] == "failed" and message in state["error_message"]
    assert await _tree(client, leader, pid) == {}


async def test_corrupt_zip_fails_cleanly(client, tmp_path):
    leader, pid, _, _ = await _leader_with_project(client, "corrupt")
    await _run(await _upload_archive(client, leader, pid, "bad.zip", b"PK\x03\x04 definitely not a zip"))
    state = await _archive_state(client, leader, pid)
    assert state["status"] == "failed" and "not a valid zip" in state["error_message"]
    assert list((tmp_path / "uploads" / "archives").glob("*")) == []


async def test_nested_archive_goes_into_a_subfolder_up_to_the_depth_limit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "archive_max_depth", 1)
    leader, pid, _, _ = await _leader_with_project(client, "nested")
    level2 = _zip({"deep.txt": b"too deep"})
    level1 = _zip({"inner.txt": b"inner", "level2.zip": level2})
    outer = _zip({"top.txt": b"top", "docs/level1.zip": level1})

    await _run(await _upload_archive(client, leader, pid, "outer.zip", outer))

    assert await _tree(client, leader, pid) == {
        "top.txt": "processing",
        "docs/level1/inner.txt": "processing",
    }
    state = await _archive_state(client, leader, pid)
    assert state["status"] == "done"
    assert [f["error"] for f in state["failed_files"]] == ["Archive nested too deeply"]


async def test_batch_mixes_archives_documents_and_rejections(client):
    leader, pid, _, _ = await _leader_with_project(client, "mixbatch")
    response = await client.post(
        f"/api/v1/projects/{pid}/documents/batch",
        files=[
            ("files", ("pack.zip", _zip({"in.txt": b"in"}), "application/zip")),
            ("files", ("note.txt", b"note", "text/plain")),
            ("files", ("empty.zip", b"", "application/zip")),
        ],
        headers=leader,
    )
    body = response.json()
    assert (body["accepted"], body["rejected"]) == (2, 1)
    by_name = {i["filename"]: i for i in body["items"]}
    assert by_name["pack.zip"]["archive"]["status"] == "extracting" and by_name["pack.zip"]["document"] is None
    assert by_name["note.txt"]["document"]["status"] == "processing" and by_name["note.txt"]["archive"] is None
    assert by_name["empty.zip"]["error"] == "File is empty"


async def test_archive_larger_than_the_cap_is_rejected_and_not_kept(client, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "max_archive_size_mb", 0)
    leader, pid, _, _ = await _leader_with_project(client, "archcap")
    response = await client.post(
        f"/api/v1/projects/{pid}/documents",
        files={"file": ("a.zip", _zip({"a.txt": b"a"}), "application/zip")},
        headers=leader,
    )
    assert response.status_code == 400
    assert list((tmp_path / "uploads" / "archives").glob("*")) == []


async def test_only_a_manager_can_upload_an_archive_and_a_folder_must_belong_to_the_project(client):
    leader, pid, team_id, admin = await _leader_with_project(client, "archacl")
    outsider_resp = await client.post("/api/v1/auth/register", json={"email": "out-arch@example.com", "password": "supersecret"})
    outsider = {"Authorization": f"Bearer {outsider_resp.json()['access_token']}"}
    denied = await client.post(
        f"/api/v1/projects/{pid}/documents", files={"file": ("a.zip", _zip({"a.txt": b"a"}), "application/zip")}, headers=outsider
    )
    assert denied.status_code == 403
    other = (await client.post(f"/api/v1/teams/{team_id}/projects", json={"name": "other"}, headers=leader)).json()["id"]
    foreign_folder = await _folder(client, leader, other, "F")
    unknown = await client.post(
        f"/api/v1/projects/{pid}/documents",
        files={"file": ("a.zip", _zip({"a.txt": b"a"}), "application/zip")},
        data={"folder_id": foreign_folder["id"]},
        headers=leader,
    )
    assert unknown.status_code == 404


async def test_dismiss_removes_finished_import_records_but_not_running_ones(client):
    leader, pid, _, _ = await _leader_with_project(client, "dismiss")
    archive = await _upload_archive(client, leader, pid, "a.zip", _zip({"a.txt": b"a"}))
    running = await client.delete(f"/api/v1/projects/{pid}/archives/{archive['id']}", headers=leader)
    assert running.status_code == 400
    await _run(archive)
    assert (await client.delete(f"/api/v1/projects/{pid}/archives/{archive['id']}", headers=leader)).status_code == 204
    assert (await _listing(client, leader, pid))["archives"] == []
    assert (await client.delete(f"/api/v1/projects/{pid}/archives/{archive['id']}", headers=leader)).status_code == 404


async def test_rerunning_a_finished_import_does_nothing(client, queued):
    leader, pid, _, _ = await _leader_with_project(client, "rerun")
    archive = await _run(await _upload_archive(client, leader, pid, "a.zip", _zip({"a.txt": b"a"})))
    jobs = len(queued)
    await archive_service.run_archive_import(uuid.UUID(archive["id"]))
    assert len(queued) == jobs and list(await _tree(client, leader, pid)) == ["a.txt"]


@pytest.mark.skipif(shutil.which("7z") is None, reason="7z binary not available")
async def test_7z_archive_is_extracted_with_the_same_rules(client, tmp_path):
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "a.txt").write_text("a")
    (src / "sub" / "b.txt").write_text("b")
    (src / "sub" / "x.shx").write_text("junk")
    (src / "plan.dwg").write_bytes(b"AC1027")
    archive_file = tmp_path / "pack.7z"
    subprocess.run(["7z", "a", "-bso0", "-bsp0", str(archive_file), "."], cwd=src, check=True)

    leader, pid, _, _ = await _leader_with_project(client, "sevenz")
    await _run(await _upload_archive(client, leader, pid, "pack.7z", archive_file.read_bytes()))

    assert await _tree(client, leader, pid) == {"a.txt": "processing", "sub/b.txt": "processing", "plan.dwg": "unsupported"}
    state = await _archive_state(client, leader, pid)
    assert state["status"] == "done" and state["skipped_files"] == 1


@pytest.mark.skipif(shutil.which("7z") is None, reason="7z binary not available")
async def test_corrupt_7z_fails_cleanly(client):
    leader, pid, _, _ = await _leader_with_project(client, "bad7z")
    await _run(await _upload_archive(client, leader, pid, "bad.7z", b"7z\xbc\xaf\x27\x1c garbage garbage garbage"))
    state = await _archive_state(client, leader, pid)
    assert state["status"] == "failed" and state["error_message"]


@pytest.mark.skipif(shutil.which("7z") is None, reason="7z binary not available")
async def test_tool_that_writes_empty_files_for_an_unsupported_method_fails_the_archive(client, tmp_path, monkeypatch):
    """Debian's 7-Zip cannot decode RAR and writes 0-byte files instead of failing: importing those silently would be
    worse than an error."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("not empty")
    archive_file = tmp_path / "pack.7z"
    subprocess.run(["7z", "a", "-bso0", "-bsp0", str(archive_file), "."], cwd=src, check=True)

    def writes_empty_files(_archive, dest):
        (dest / "a.txt").write_bytes(b"")

    monkeypatch.setattr(archive_service, "_run_cli_extract", writes_empty_files)
    leader, pid, _, _ = await _leader_with_project(client, "emptyout")
    await _run(await _upload_archive(client, leader, pid, "pack.7z", archive_file.read_bytes()))

    state = await _archive_state(client, leader, pid)
    assert state["status"] == "failed" and "compression method" in state["error_message"]
    assert await _tree(client, leader, pid) == {}
