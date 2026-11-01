"""volume report module: vr_* tables

Revision ID: 0014_volume_report
Revises: 0013_accounting_access
Create Date: 2026-11-01

Adds the tables of the `volume_report` feature (see .agents/flows/volume-report.md). Purely additive; the feature
stays inert unless VOLUME_REPORT_ENABLED. Catalog/lexicon/conversion seed rows are inserted lazily by the service
(`seed.ensure_seeded`), not here, so a fresh `create_all` test schema behaves like a migrated one.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings

settings = get_settings()

revision: str = "0014_volume_report"
down_revision: Union[str, None] = "0013_accounting_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    postgresql.ENUM('volume', 'area', 'length', 'mass', 'area_thickness', 'volume_distance', 'time', 'nonphysical', name='vr_dimension').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('item_hint', 'role', 'hard_exclusion', 'noise', name='vr_lexicon_kind').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('road', 'mining', 'other', name='vr_site_kind').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('week', 'month', name='vr_period_type').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('draft', 'processing', 'awaiting_user', 'needs_review', 'ready', 'published', 'failed', name='vr_report_status').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('running', 'completed', 'awaiting_user', 'failed', 'cancelled', name='vr_run_status').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('counted', 'excluded', 'nonphysical', 'unmatched', 'needs_input', name='vr_disposition').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('supply', 'execute', 'combined', 'na', name='vr_role').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('surcharge', 'demolition', 'trenching', 'pointing', 'site_setup', 'duplicate', 'haul_only', 'nonphysical', 'other', name='vr_exclude_reason').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('human', 'system', 'agent', name='vr_decision_source').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('site', 'company', 'holding', name='vr_result_scope').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('memory', 'agent', 'human', 'system', name='vr_class_source').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('choice', 'multi_choice', 'number', 'text', 'confirm_group', name='vr_question_kind').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('open', 'answered', 'skipped', 'superseded', name='vr_question_status').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('pending', 'parsed', 'failed', name='vr_file_status').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('counted', 'supply_ignored', 'supply_only_not_counted', 'duplicate_ignored', 'excluded', 'unmatched', 'nonphysical', 'unit_mismatch', 'no_conversion', 'site_kind_mismatch', 'needs_input', name='vr_effect').create(op.get_bind(), checkfirst=True)

    op.create_table('vr_companies',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )

    op.create_table('vr_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('title_fa', sa.String(length=200), nullable=False),
    sa.Column('description_fa', sa.Text(), nullable=False),
    sa.Column('dimension', postgresql.ENUM('volume', 'area', 'length', 'mass', 'area_thickness', 'volume_distance', 'time', 'nonphysical', name='vr_dimension', create_type=False), nullable=False),
    sa.Column('output_unit', sa.String(length=20), nullable=False),
    sa.Column('decimals', sa.Integer(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_rollup', sa.Boolean(), nullable=False),
    sa.Column('rollup_of', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('mining_only', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )

    op.create_table('vr_lexicon',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('token', sa.String(length=64), nullable=False),
    sa.Column('phrases', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('kind', postgresql.ENUM('item_hint', 'role', 'hard_exclusion', 'noise', name='vr_lexicon_kind', create_type=False), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token')
    )

    op.create_table('vr_settings',
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )

    op.create_table('vr_sites',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=500), nullable=False),
    sa.Column('name_norm', sa.String(length=500), nullable=False),
    sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('kind', postgresql.ENUM('road', 'mining', 'other', name='vr_site_kind', create_type=False), nullable=False),
    sa.Column('kind_confirmed', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['vr_companies.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'name_norm', name='uq_vr_sites_company_name')
    )

    op.create_table('vr_conversions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('item_id', sa.UUID(), nullable=True),
    sa.Column('site_id', sa.UUID(), nullable=True),
    sa.Column('value', sa.Numeric(precision=20, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=32), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['vr_items.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['vr_sites.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_vr_conversions_scope', 'vr_conversions', ['key', sa.text("coalesce(item_id, '00000000-0000-0000-0000-000000000000'::uuid)"), sa.text("coalesce(site_id, '00000000-0000-0000-0000-000000000000'::uuid)")], unique=True)

    op.create_table('vr_reports',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('period_type', postgresql.ENUM('week', 'month', name='vr_period_type', create_type=False), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('period_label', sa.String(length=100), nullable=False),
    sa.Column('status', postgresql.ENUM('draft', 'processing', 'awaiting_user', 'needs_review', 'ready', 'published', 'failed', name='vr_report_status', create_type=False), nullable=False),
    sa.Column('progress', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('supersedes_id', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('published_by', sa.UUID(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('catalog_version', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['published_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['supersedes_id'], ['vr_reports.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vr_reports_status'), 'vr_reports', ['status'], unique=False)
    op.create_index(op.f('ix_vr_reports_project_id'), 'vr_reports', ['project_id'], unique=False)

    op.create_table('vr_agent_runs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('pass_no', sa.Integer(), nullable=False),
    sa.Column('status', postgresql.ENUM('running', 'completed', 'awaiting_user', 'failed', 'cancelled', name='vr_run_status', create_type=False), nullable=False),
    sa.Column('model', sa.String(length=200), nullable=True),
    sa.Column('steps', sa.Integer(), nullable=False),
    sa.Column('prompt_tokens', sa.Integer(), nullable=False),
    sa.Column('completion_tokens', sa.Integer(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['report_id'], ['vr_reports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vr_agent_runs_report_id'), 'vr_agent_runs', ['report_id'], unique=False)

    op.create_table('vr_decisions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('key_hash', sa.String(length=64), nullable=False),
    sa.Column('description_norm', sa.Text(), nullable=False),
    sa.Column('unit_norm', sa.String(length=20), nullable=False),
    sa.Column('site_kind', postgresql.ENUM('road', 'mining', 'other', name='vr_site_kind', create_type=False), nullable=False),
    sa.Column('disposition', postgresql.ENUM('counted', 'excluded', 'nonphysical', 'unmatched', 'needs_input', name='vr_disposition', create_type=False), nullable=False),
    sa.Column('item_id', sa.UUID(), nullable=True),
    sa.Column('role', postgresql.ENUM('supply', 'execute', 'combined', 'na', name='vr_role', create_type=False), nullable=False),
    sa.Column('exclude_reason', postgresql.ENUM('surcharge', 'demolition', 'trenching', 'pointing', 'site_setup', 'duplicate', 'haul_only', 'nonphysical', 'other', name='vr_exclude_reason', create_type=False), nullable=True),
    sa.Column('embedding', Vector(settings.embedding_dimensions), nullable=True),
    sa.Column('hits', sa.Integer(), nullable=False),
    sa.Column('source', postgresql.ENUM('human', 'system', 'agent', name='vr_decision_source', create_type=False), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('confirmed_by', sa.UUID(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source_report_id', sa.UUID(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_by', sa.UUID(), nullable=True),
    sa.Column('catalog_version', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['confirmed_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['item_id'], ['vr_items.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_report_id'], ['vr_reports.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key_hash')
    )

    op.create_table('vr_results',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('scope', postgresql.ENUM('site', 'company', 'holding', name='vr_result_scope', create_type=False), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=True),
    sa.Column('site_id', sa.UUID(), nullable=True),
    sa.Column('item_id', sa.UUID(), nullable=False),
    sa.Column('qty', sa.Numeric(precision=20, scale=4), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('n_lines', sa.Integer(), nullable=False),
    sa.Column('has_unconfirmed', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['vr_companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['vr_items.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['report_id'], ['vr_reports.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['vr_sites.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_vr_results_cell', 'vr_results', ['report_id', 'scope', sa.text("coalesce(company_id, '00000000-0000-0000-0000-000000000000'::uuid)"), sa.text("coalesce(site_id, '00000000-0000-0000-0000-000000000000'::uuid)"), 'item_id'], unique=True)
    op.create_index(op.f('ix_vr_results_report_id'), 'vr_results', ['report_id'], unique=False)

    op.create_table('vr_snapshots',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('catalog_version', sa.Integer(), nullable=False),
    sa.Column('catalog_hash', sa.String(length=64), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['report_id'], ['vr_reports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('report_id', name='uq_vr_snapshots_report')
    )

    op.create_table('vr_agent_steps',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('step_no', sa.Integer(), nullable=False),
    sa.Column('tool_name', sa.String(length=100), nullable=False),
    sa.Column('arguments', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('result_summary', sa.Text(), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['vr_agent_runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vr_agent_steps_run_id'), 'vr_agent_steps', ['run_id'], unique=False)

    op.create_table('vr_classifications',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('group_key', sa.String(length=64), nullable=False),
    sa.Column('disposition', postgresql.ENUM('counted', 'excluded', 'nonphysical', 'unmatched', 'needs_input', name='vr_disposition', create_type=False), nullable=False),
    sa.Column('item_id', sa.UUID(), nullable=True),
    sa.Column('role', postgresql.ENUM('supply', 'execute', 'combined', 'na', name='vr_role', create_type=False), nullable=False),
    sa.Column('exclude_reason', postgresql.ENUM('surcharge', 'demolition', 'trenching', 'pointing', 'site_setup', 'duplicate', 'haul_only', 'nonphysical', 'other', name='vr_exclude_reason', create_type=False), nullable=True),
    sa.Column('source', postgresql.ENUM('memory', 'agent', 'human', 'system', name='vr_class_source', create_type=False), nullable=False),
    sa.Column('confirmed', sa.Boolean(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('decision_id', sa.UUID(), nullable=True),
    sa.Column('decided_by', sa.UUID(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['decision_id'], ['vr_decisions.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['item_id'], ['vr_items.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['report_id'], ['vr_reports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('report_id', 'group_key', name='uq_vr_classifications_group')
    )
    op.create_index(op.f('ix_vr_classifications_report_id'), 'vr_classifications', ['report_id'], unique=False)

    op.create_table('vr_questions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=True),
    sa.Column('kind', postgresql.ENUM('choice', 'multi_choice', 'number', 'text', 'confirm_group', name='vr_question_kind', create_type=False), nullable=False),
    sa.Column('spec', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('group_keys', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('impact_score', sa.Float(), nullable=False),
    sa.Column('status', postgresql.ENUM('open', 'answered', 'skipped', 'superseded', name='vr_question_status', create_type=False), nullable=False),
    sa.Column('answer', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('answered_by', sa.UUID(), nullable=True),
    sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['answered_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['report_id'], ['vr_reports.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['run_id'], ['vr_agent_runs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vr_questions_report_id'), 'vr_questions', ['report_id'], unique=False)

    op.create_table('vr_report_files',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=True),
    sa.Column('filename', sa.String(length=500), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('status', postgresql.ENUM('pending', 'parsed', 'failed', name='vr_file_status', create_type=False), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('sheet_log', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('suggested_company', sa.String(length=300), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['vr_companies.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['report_id'], ['vr_reports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('report_id', 'document_id', name='uq_vr_report_files_doc')
    )
    op.create_index(op.f('ix_vr_report_files_report_id'), 'vr_report_files', ['report_id'], unique=False)

    op.create_table('vr_lines',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_file_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('sheet_name', sa.String(length=255), nullable=False),
    sa.Column('row_no', sa.Integer(), nullable=False),
    sa.Column('section_heading', sa.Text(), nullable=True),
    sa.Column('description_raw', sa.Text(), nullable=False),
    sa.Column('description_norm', sa.Text(), nullable=False),
    sa.Column('tokens', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('unit_raw', sa.String(length=200), nullable=False),
    sa.Column('unit_norm', sa.String(length=20), nullable=False),
    sa.Column('unit_dim', postgresql.ENUM('volume', 'area', 'length', 'mass', 'area_thickness', 'volume_distance', 'time', 'nonphysical', name='vr_dimension', create_type=False), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=20, scale=4), nullable=False),
    sa.Column('flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('group_key', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['report_file_id'], ['vr_report_files.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['vr_sites.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('report_file_id', 'sheet_name', 'row_no', name='uq_vr_lines_row')
    )
    op.create_index(op.f('ix_vr_lines_site_id'), 'vr_lines', ['site_id'], unique=False)
    op.create_index(op.f('ix_vr_lines_group_key'), 'vr_lines', ['group_key'], unique=False)
    op.create_index(op.f('ix_vr_lines_report_file_id'), 'vr_lines', ['report_file_id'], unique=False)

    op.create_table('vr_line_results',
    sa.Column('line_id', sa.UUID(), nullable=False),
    sa.Column('effect', postgresql.ENUM('counted', 'supply_ignored', 'supply_only_not_counted', 'duplicate_ignored', 'excluded', 'unmatched', 'nonphysical', 'unit_mismatch', 'no_conversion', 'site_kind_mismatch', 'needs_input', name='vr_effect', create_type=False), nullable=False),
    sa.Column('item_id', sa.UUID(), nullable=True),
    sa.Column('output_qty', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('output_unit', sa.String(length=20), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('unconfirmed', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['vr_items.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['line_id'], ['vr_lines.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('line_id')
    )

    op.execute(
        "CREATE INDEX ix_vr_decisions_embedding_hnsw ON vr_decisions "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_vr_decisions_description_trgm ON vr_decisions "
        "USING gin (description_norm gin_trgm_ops)"
    )


def downgrade() -> None:
    op.drop_table('vr_line_results')
    op.drop_table('vr_lines')
    op.drop_table('vr_report_files')
    op.drop_table('vr_questions')
    op.drop_table('vr_classifications')
    op.drop_table('vr_agent_steps')
    op.drop_table('vr_snapshots')
    op.drop_table('vr_results')
    op.drop_table('vr_decisions')
    op.drop_table('vr_agent_runs')
    op.drop_table('vr_reports')
    op.drop_table('vr_conversions')
    op.drop_table('vr_sites')
    op.drop_table('vr_settings')
    op.drop_table('vr_lexicon')
    op.drop_table('vr_items')
    op.drop_table('vr_companies')
    postgresql.ENUM(name='vr_dimension').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_lexicon_kind').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_site_kind').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_period_type').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_report_status').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_run_status').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_disposition').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_role').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_exclude_reason').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_decision_source').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_result_scope').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_class_source').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_question_kind').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_question_status').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_file_status').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vr_effect').drop(op.get_bind(), checkfirst=True)
