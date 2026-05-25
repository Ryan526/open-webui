"""Add QC projects, revisions, and reports

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-04-16 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
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


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "qc_project" not in existing_tables:
        op.create_table(
            "qc_project",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_project_user_id", "qc_project", ["user_id"])

    # qc_job additions
    # NB: FK constraints are intentionally omitted on added columns for broad DB
    # compatibility (SQLite ALTER limitations). App-level enforcement is used.
    job_cols = _column_names("qc_job")
    with op.batch_alter_table("qc_job") as batch:
        if "project_id" not in job_cols:
            batch.add_column(sa.Column("project_id", sa.Text(), nullable=True))
        if "previous_job_id" not in job_cols:
            batch.add_column(sa.Column("previous_job_id", sa.Text(), nullable=True))
        if "revision_label" not in job_cols:
            batch.add_column(sa.Column("revision_label", sa.Text(), nullable=True))
        if "revision_index" not in job_cols:
            batch.add_column(sa.Column("revision_index", sa.Integer(), nullable=True))

    _safe_create_index("idx_qc_job_project_id", "qc_job", ["project_id"])
    _safe_create_index("idx_qc_job_previous_job_id", "qc_job", ["previous_job_id"])

    # qc_finding additions
    finding_cols = _column_names("qc_finding")
    with op.batch_alter_table("qc_finding") as batch:
        if "previous_finding_id" not in finding_cols:
            batch.add_column(sa.Column("previous_finding_id", sa.Text(), nullable=True))
        if "revision_state" not in finding_cols:
            batch.add_column(sa.Column("revision_state", sa.Text(), nullable=True))

    _safe_create_index(
        "idx_qc_finding_previous_finding_id",
        "qc_finding",
        ["previous_finding_id"],
    )

    # qc_report new table
    existing_tables = set(get_existing_tables())
    if "qc_report" not in existing_tables:
        op.create_table(
            "qc_report",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column(
                "job_id",
                sa.Text(),
                sa.ForeignKey("qc_job.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("report_type", sa.Text(), nullable=False),
            sa.Column(
                "file_id",
                sa.Text(),
                sa.ForeignKey("file.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_report_job_id", "qc_report", ["job_id"])
        op.create_index("idx_qc_report_report_type", "qc_report", ["report_type"])


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


def downgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "qc_report" in existing_tables:
        op.drop_table("qc_report")

    with op.batch_alter_table("qc_finding") as batch:
        try:
            batch.drop_column("revision_state")
        except Exception:
            pass
        try:
            batch.drop_column("previous_finding_id")
        except Exception:
            pass

    with op.batch_alter_table("qc_job") as batch:
        for col in ("revision_index", "revision_label", "previous_job_id", "project_id"):
            try:
                batch.drop_column(col)
            except Exception:
                pass

    if "qc_project" in existing_tables:
        op.drop_table("qc_project")
