import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.agent.schemas import ToolExecutionResult
from app.features.agent.scope import resolve_retrieval_scope
from app.features.agent.tools.base import BaseTool
from app.features.documents import folder_service
from app.features.documents.models import Document, DocumentFolder, DocumentStatus

# Entries per call: a folder can hold hundreds of files, and every line costs prompt tokens.
_FILES_PER_CALL = 100
_MAX_SUBFOLDERS = 200
_MAX_TREE_FOLDERS = 40
_MAX_TREE_ROOT_FILES = 15


def _count_text(counts: dict[str, int]) -> str:
    """"12 files" or "12 files, 3 not ready (failed 2, processing 1)" from per-status counts."""
    total = sum(counts.values())
    other = {k: v for k, v in counts.items() if k != DocumentStatus.READY.value}
    text = f"{total} files"
    if other:
        text += f", {sum(other.values())} not ready (" + ", ".join(f"{k} {v}" for k, v in sorted(other.items())) + ")"
    return text


def _status_text(document: Document) -> str:
    if document.status == DocumentStatus.FAILED and document.error_message:
        return f"failed: {' '.join(document.error_message.split())[:80]}"
    return document.status.value


async def project_tree_summary(db: AsyncSession, project_id: uuid.UUID) -> str:
    """The project's top level for the system prompt: each top-level folder with recursive file counts, then loose files."""
    listing = await folder_service.list_folder(db, project_id, None)
    lines: list[str] = []
    for entry in listing["folders"][:_MAX_TREE_FOLDERS]:
        lines.append(f"- {entry['folder'].name}/ ({_count_text(entry['status_counts'])})")
    if len(listing["folders"]) > _MAX_TREE_FOLDERS:
        lines.append(f"- ... {len(listing['folders']) - _MAX_TREE_FOLDERS} more folders (browse_folder with an empty path lists them)")
    documents = listing["documents"]
    for document in documents[:_MAX_TREE_ROOT_FILES]:
        lines.append(f"- {document.filename} (file, document_id: {document.id}, {_status_text(document)})")
    if len(documents) > _MAX_TREE_ROOT_FILES:
        lines.append(f"- ... {len(documents) - _MAX_TREE_ROOT_FILES} more files at the top level")
    return "\n".join(lines)


class BrowseFolderTool(BaseTool):
    name = "browse_folder"
    description = (
        "Browse the project's folder tree like a file manager. Give a folder path (e.g. 'امور مربوط به تعدیل/تعدیل شماره2'; "
        "empty = the top level) to list its subfolders (with file counts) and its files (with document_id and status). "
        "Use it to find where a document lives when the question names a folder, a topic area or a file, then open the "
        "file with read_document_pages / read_entire_document. A file that is not 'ready' (processing, failed, "
        "unsupported, cancelled) exists but cannot be read or searched yet."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Folder path separated by '/'; empty or omitted for the top level"},
            "offset": {"type": "integer", "description": f"Skip this many files (a folder lists {_FILES_PER_CALL} files per call)"},
        },
    }

    def is_available_for(self, context=None, conversation=None) -> bool:
        return context is not None and conversation is not None and resolve_retrieval_scope(context, conversation) is not None

    async def execute(self, *, db, context, conversation, path: str = "", offset: int = 0, **_: Any) -> ToolExecutionResult:
        project_id = resolve_retrieval_scope(context, conversation)
        if project_id is None:
            return ToolExecutionResult(text="This conversation isn't linked to any project.")
        folders = await folder_service.load_folders(db, project_id)
        try:
            folder_id = folder_service.resolve_path(folders, path)
        except Exception as exc:  # NotFoundError: show where the model can go from the top level instead of a bare error
            top = sorted(f.name for f in folders.values() if f.parent_id is None)
            return ToolExecutionResult(text=f"{getattr(exc, 'detail', exc)}. Top-level folders: " + (", ".join(top) or "(none)"))

        listing = await folder_service.list_folder(db, project_id, folder_id)
        where = "/".join(f.name for f in listing["breadcrumb"]) or "(top level)"
        lines = [f"Folder: {where}"]

        subfolders = listing["folders"]
        if subfolders:
            lines.append(f"Subfolders ({len(subfolders)}):")
            lines += [f"- {e['folder'].name}/ ({_count_text(e['status_counts'])})" for e in subfolders[:_MAX_SUBFOLDERS]]

        documents = listing["documents"]
        start = max(int(offset or 0), 0)
        page = documents[start : start + _FILES_PER_CALL]
        if documents:
            lines.append(f"Files ({len(documents)}" + (f", showing {start + 1}-{start + len(page)}" if len(documents) > len(page) else "") + "):")
            lines += [f"- {d.filename} | document_id: {d.id} | {_status_text(d)}" for d in page]
            if start + len(page) < len(documents):
                lines.append(f"(more files: call again with offset={start + len(page)})")
        if not subfolders and not documents:
            lines.append("(empty)")
        return ToolExecutionResult(text="\n".join(lines))
