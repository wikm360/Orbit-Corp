from typing import Any

from app.features.agent.schemas import ToolExecutionResult
from app.features.agent.tools.base import BaseTool
from app.features.db_connector import service as db_connector_service


class AskAccountingDbTool(BaseTool):
    name = "ask_accounting_db"
    description = (
        "Query the company's official Rahkaran accounting and financial database. "
        "Covers general ledger, financial statements, trial balances, vouchers, contracts & claims, "
        "counterparty balances (vendors, customers), payroll & monthly salaries, employees, "
        "fixed assets, bank accounts, and loans/guarantees. Use this tool whenever a question asks "
        "about company financials, project costs, contract values, payroll, employee counts, or account balances. "
        "Call it once per question. The exact SQL and the full result table are shown to the user automatically with your reply, "
        "so do not repeat the table; summarise it and quote figures exactly as returned."
    )
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": (
                    "A self-contained question in Persian about accounting, financial figures, contracts, or payroll. "
                    "Include every name, period and contract needed (resolve references like 'and last year?' from the chat first)."
                ),
            }
        },
        "required": ["question"],
    }

    async def execute(
        self,
        *,
        db,
        context,
        conversation,
        question: str,
        **_: Any,
    ) -> ToolExecutionResult:
        answer = await db_connector_service.run_accounting_query(
            db,
            question=question,
            user_id=context.id,
            conversation_id=conversation.id,
            include_sql_in_text=False,
        )
        return ToolExecutionResult(text=answer.text, artifacts=[answer.artifact] if answer.artifact else [])

