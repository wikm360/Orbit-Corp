import asyncio
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.features.agent.schemas import SourceCitation, ToolExecutionResult
from app.features.agent.scope import resolve_retrieval_scope
from app.features.agent.tools.base import BaseTool
from app.features.agent.tools.document_tools import _DOCUMENT_ID_PROPERTY, _resolve_document_id
from app.features.documents import service as documents_service
from app.features.documents import spreadsheet

settings = get_settings()


async def _load_spreadsheet(db, context, conversation, identifier: str):
    """Resolves the document through the usual access check, then loads its tables (parsed once, cached beside the file)."""
    project_id = resolve_retrieval_scope(context, conversation)
    document_id = await _resolve_document_id(db, identifier, project_id=project_id, conversation_id=conversation.id)
    document = await documents_service.get_accessible_document(
        db, document_id, project_id=project_id, conversation_id=conversation.id
    )
    if not spreadsheet.is_spreadsheet(document.file_path):
        raise BadRequestError(f"'{document.filename}' is not a spreadsheet; use the other document tools")
    tables = await asyncio.to_thread(spreadsheet.load_tables, document.file_path)
    if not tables:
        raise BadRequestError(f"'{document.filename}' has no data rows")
    return document, tables


class DescribeSpreadsheetTool(BaseTool):
    name = "describe_spreadsheet"
    description = (
        "Show the structure of an Excel/CSV document: sheets, column names with their types, how many cells are filled, "
        "the distinct values of small categorical columns, and the first rows. Call it BEFORE query_spreadsheet on a file "
        "you have not described yet in this chat, so the SQL uses real column names. Accepts document_id (UUID) or filename."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_DOCUMENT_ID_PROPERTY,
            "sheet": {"type": "string", "description": "Only this sheet (default: all sheets)"},
        },
        "required": ["document_id"],
    }

    async def execute(
        self, *, db, context, conversation, document_id: str, sheet: str | None = None, **_: Any
    ) -> ToolExecutionResult:
        document, tables = await _load_spreadsheet(db, context, conversation, document_id)
        text = spreadsheet.describe_tables(tables, sheet)
        return ToolExecutionResult(text=f"Spreadsheet: {document.filename}\n{text}")


class QuerySpreadsheetTool(BaseTool):
    name = "query_spreadsheet"
    description = (
        "Run ONE read-only SQL SELECT (SQLite dialect) over the sheets of an Excel/CSV document. Use it for EVERY question "
        "that needs an exact value, a lookup of a person/row, a filter, a count, a sum/average or a ranking in a spreadsheet - "
        "never read numbers out of search/read text for those. Each sheet is a table named after the sheet (double-quoted); "
        "columns are named by the header row (double-quote them); `_row` is the row number in the original file. "
        "Filter people/names with LIKE '%part%' (text is normalized: ي→ی, ك→ک, Persian digits→0-9). "
        "Let SQL do ALL arithmetic (SUM/AVG/COUNT/GROUP BY) - never add, compare or re-derive numbers yourself, not even ones "
        "already shown earlier in the chat: run a new query. Use only column names listed by describe_spreadsheet (an unknown name "
        "is an error). Names of one item are often spelled several ways (Sub base / Sub Base layer): match the common stem with "
        "LIKE and GROUP BY the name column to show what was included. Include `_row` in the SELECT so you can cite it. If no row matches, report that nothing was found - the result may list similar values to confirm "
        "with the user, never silently substitute another name. Accepts document_id (UUID) or filename."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_DOCUMENT_ID_PROPERTY,
            "sql": {"type": "string", "description": "A single SELECT statement"},
            "max_rows": {"type": "integer", "description": "Rows to return (default 50, capped)"},
        },
        "required": ["document_id", "sql"],
    }

    async def execute(
        self,
        *,
        db,
        context,
        conversation,
        document_id: str,
        sql: str,
        max_rows: int | None = None,
        **_: Any,
    ) -> ToolExecutionResult:
        document, tables = await _load_spreadsheet(db, context, conversation, document_id)
        cap = settings.spreadsheet_query_max_rows
        try:
            wanted = int(max_rows) if max_rows else 50
        except (TypeError, ValueError):
            raise BadRequestError("'max_rows' must be an integer")
        limit = max(1, min(wanted, cap))
        result = await asyncio.to_thread(
            spreadsheet.run_query,
            tables,
            str(sql),
            max_rows=limit,
            timeout_seconds=settings.spreadsheet_query_timeout_seconds,
        )

        lines = [f"Spreadsheet: {document.filename} | sheet(s) used: {', '.join(result.sheets) or '-'}"]
        if not result.rows:
            lines.append("Rows returned: 0 (no row matched the query).")
            if result.suggestions:
                lines.append(
                    "Similar values in the file (confirm with the user before using one, do not assume): "
                    + "; ".join(result.suggestions)
                )
        else:
            lines.append(spreadsheet.markdown_table(result.columns, result.rows))
            lines.append(
                f"Rows returned: {len(result.rows)}"
                + (f" (output cut at {limit} rows; more match - narrow the query or aggregate in SQL)" if result.truncated else "")
            )
            letters = spreadsheet.column_letters_for(tables, result.columns)
            if letters:
                lines.append("File columns: " + ", ".join(f"{name}={letter}" for name, letter in letters.items()))

        snippet = lines[1][:300]
        citation = SourceCitation(
            document_id=str(document.id),
            document_filename=document.filename,
            chunk_index=-1,
            snippet=snippet,
            score=1.0,
        )
        return ToolExecutionResult(text="\n".join(lines), citations=[citation])
