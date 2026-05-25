"""Add QC finding intelligence (duplicates + suppression)

Revision ID: e5f6a7b8c9d0
Revises: d5e6f7a8b9c0
Create Date: 2026-04-16 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set:
    from sqlalchemy import Inspector

    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    try:
        return {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return set()


def _safe_create_index(name: str, table: str, cols: list) -> None:
    from sqlalchemy import Inspector

    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    try:
        existing = {ix["name"] for ix in inspector.get_indexes(table)}
    except Exception:
        existing = set()
    if name not in existing:
        op.create_index(name, table, cols)


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    # qc_finding additions: canonical_finding_id + dup_cluster_key (no FKs for SQLite compat)
    finding_cols = _column_names("qc_finding")
    with op.batch_alter_table("qc_finding") as batch:
        if "canonical_finding_id" not in finding_cols:
            batch.add_column(sa.Column("canonical_finding_id", sa.Text(), nullable=True))
        if "dup_cluster_key" not in finding_cols:
            batch.add_column(sa.Column("dup_cluster_key", sa.Text(), nullable=True))

    _safe_create_index(
        "idx_qc_finding_canonical_finding_id",
        "qc_finding",
        ["canonical_finding_id"],
    )
    _safe_create_index(
        "idx_qc_finding_dup_cluster_key",
        "qc_finding",
        ["dup_cluster_key"],
    )

    if "qc_suppression_rule" not in existing_tables:
        op.create_table(
            "qc_suppression_rule",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("scope", sa.Text(), nullable=False),  # template|project|global
            sa.Column("template_id", sa.Text(), nullable=True),
            sa.Column("project_id", sa.Text(), nullable=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("match_type", sa.Text(), nullable=False),
            sa.Column("match_value", sa.Text(), nullable=False),
            sa.Column("severity_filter", sa.Text(), nullable=True),
            sa.Column("page_tag_filter", sa.Text(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_hit_at", sa.BigInteger(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "idx_qc_suppression_rule_template_id",
            "qc_suppression_rule",
            ["template_id"],
        )
        op.create_index(
            "idx_qc_suppression_rule_project_id",
            "qc_suppression_rule",
            ["project_id"],
        )
        op.create_index(
            "idx_qc_suppression_rule_scope_enabled",
            "qc_suppression_rule",
            ["scope", "enabled"],
        )

    existing_tables = set(get_existing_tables())
    if "qc_suppression_event" not in existing_tables:
        op.create_table(
            "qc_suppression_event",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column(
                "rule_id",
                sa.Text(),
                sa.ForeignKey("qc_suppression_rule.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "job_id",
                sa.Text(),
                sa.ForeignKey("qc_job.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("document_id", sa.Text(), nullable=True),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("suppressed_title", sa.Text(), nullable=True),
            sa.Column("suppressed_payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "idx_qc_suppression_event_rule_id",
            "qc_suppression_event",
            ["rule_id"],
        )
        op.create_index(
            "idx_qc_suppression_event_job_id",
            "qc_suppression_event",
            ["job_id"],
        )


def downgrade() -> None:
    existing_tables = set(get_existing_tables())
    if "qc_suppression_event" in existing_tables:
        op.drop_table("qc_suppression_event")
    if "qc_suppression_rule" in existing_tables:
        op.drop_table("qc_suppression_rule")

    with op.batch_alter_table("qc_finding") as batch:
        for col in ("dup_cluster_key", "canonical_finding_id"):
            try:
                batch.drop_column(col)
            except Exception:
                pass
