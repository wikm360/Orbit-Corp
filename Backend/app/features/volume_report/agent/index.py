"""Read model of a report's unique groups for the agent and the question code. Holds quantities (for impact scores,
computed by code) but the agent tools never print them."""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.features.volume_report import service
from app.features.volume_report.models import Classification, Disposition, Item, Question, QuestionStatus, Report

ID_LEN = 10


@dataclass
class Group:
    key: str
    description: str
    unit: str
    unit_dim: str
    site_kind: str
    site_ids: set[uuid.UUID] = field(default_factory=set)
    sections: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)
    role_hint: str = "na"
    n_lines: int = 0
    quantity: Decimal = Decimal(0)
    flags: set[str] = field(default_factory=set)
    twin_descriptions: list[str] = field(default_factory=list)
    classification: Classification | None = None
    asked: bool = False

    @property
    def id(self) -> str:
        return self.key[:ID_LEN]

    @property
    def final(self) -> bool:
        """Has a status the agent should not revisit: any non-needs_input classification, or an open question."""
        c = self.classification
        return self.asked or (c is not None and c.disposition != Disposition.NEEDS_INPUT)

    @property
    def locked(self) -> bool:
        """Confirmed by a human, memory or a system rule: the agent may not overwrite it."""
        c = self.classification
        return c is not None and c.confirmed


class GroupIndex:
    def __init__(self, groups: list[Group], items: dict[str, Item]):
        self.groups = groups
        self.by_key = {g.key: g for g in groups}
        self.items = items  # active items by key

    @classmethod
    async def load(cls, db: AsyncSession, report: Report) -> "GroupIndex":
        pairs = await service._report_lines(db, report.id)
        descriptions = {(line.report_file_id, line.sheet_name, line.row_no): line.description_raw for line, _ in pairs}
        classes = {c.group_key: c for c in (await db.execute(select(Classification).where(Classification.report_id == report.id))).scalars()}
        asked: set[str] = set()
        for q in (await db.execute(select(Question).where(Question.report_id == report.id, Question.status == QuestionStatus.OPEN))).scalars():
            asked.update(q.group_keys)
        groups: dict[str, Group] = {}
        for line, site in pairs:
            g = groups.get(line.group_key)
            if g is None:
                g = groups[line.group_key] = Group(
                    key=line.group_key, description=line.description_raw, unit=line.unit_norm, unit_dim=line.unit_dim.value,
                    site_kind=site.kind.value, tokens=list(line.tokens), role_hint=line.flags.get("role_hint", "na"),
                    classification=classes.get(line.group_key), asked=line.group_key in asked,
                )
            g.site_ids.add(site.id)
            g.n_lines += 1
            g.quantity += line.quantity
            if line.section_heading and line.section_heading not in g.sections and len(g.sections) < 3:
                g.sections.append(line.section_heading)
            g.flags.update(k for k in ("negative_qty", "has_surcharge_word", "nonphysical_unit") if line.flags.get(k))
            for row in line.flags.get("twin_rows", [])[:2]:
                text = descriptions.get((line.report_file_id, line.sheet_name, row))
                if text and text not in g.twin_descriptions:
                    g.twin_descriptions.append(text)
        items = {i.key: i for i in (await db.execute(select(Item).where(Item.is_active.is_(True)))).scalars()}
        return cls(list(groups.values()), items)

    def resolve(self, group_id: str) -> Group:
        """Accepts the short id (or a full key). Never trusts the model: unknown/ambiguous ids are rejected."""
        group_id = (group_id or "").strip().lower()
        if len(group_id) < ID_LEN:
            raise BadRequestError(f"Invalid group_id: {group_id!r}")
        matches = [g for g in self.groups if g.key.startswith(group_id)]
        if not matches:
            raise NotFoundError(f"Unknown group_id: {group_id}")
        if len(matches) > 1:
            raise BadRequestError(f"Ambiguous group_id: {group_id}")
        return matches[0]

    def unresolved(self) -> list[Group]:
        return [g for g in self.groups if not g.final]
