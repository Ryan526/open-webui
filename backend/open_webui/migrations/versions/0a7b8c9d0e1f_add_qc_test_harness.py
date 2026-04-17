"""Add QC test harness

Revision ID: 0a7b8c9d0e1f
Revises: f6a7b8c9d0e1
Create Date: 2026-04-16 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "0a7b8c9d0e1f"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
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

    if "qc_test_set" not in existing_tables:
        op.create_table(
            "qc_test_set",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_test_set_user_id", "qc_test_set", ["user_id"])

    existing_tables = set(get_existing_tables())
    if "qc_test_set_document" not in existing_tables:
        op.create_table(
            "qc_test_set_document",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column(
                "test_set_id",
                sa.Text(),
                sa.ForeignKey("qc_test_set.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "file_id",
                sa.Text(),
                sa.ForeignKey("file.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("page_count", sa.Integer(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "idx_qc_test_set_document_test_set_id",
            "qc_test_set_document",
            ["test_set_id"],
        )

    existing_tables = set(get_existing_tables())
    if "qc_test_set_expected_finding" not in existing_tables:
        op.create_table(
            "qc_test_set_expected_finding",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column(
                "test_set_id",
                sa.Text(),
                sa.ForeignKey("qc_test_set.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "document_id",
                sa.Text(),
                sa.ForeignKey("qc_test_set_document.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("checklist_item_id", sa.Text(), nullable=True),
            sa.Column("severity", sa.Text(), nullable=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("location", sa.JSON(), nullable=True),
            sa.Column("match_title_patterns", sa.JSON(), nullable=True),
            sa.Column("seeded_from_finding_id", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "idx_qc_test_set_expected_finding_test_set_id",
            "qc_test_set_expected_finding",
            ["test_set_id"],
        )
        op.create_index(
            "idx_qc_test_set_expected_finding_document_id",
            "qc_test_set_expected_finding",
            ["document_id"],
        )

    existing_tables = set(get_existing_tables())
    if "qc_test_run" not in existing_tables:
        op.create_table(
            "qc_test_run",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column(
                "test_set_id",
                sa.Text(),
                sa.ForeignKey("qc_test_set.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("template_id", sa.Text(), nullable=True),
            sa.Column("template_version_id", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("shadow_job_id", sa.Text(), nullable=True),
            sa.Column("metrics", sa.JSON(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_test_run_user_id", "qc_test_run", ["user_id"])
        op.create_index("idx_qc_test_run_test_set_id", "qc_test_run", ["test_set_id"])
        op.create_index("idx_qc_test_run_template_id", "qc_test_run", ["template_id"])

    # qc_job.test_run_id (FK omitted for SQLite compat; app-level enforced)
    job_cols = _column_names("qc_job")
    with op.batch_alter_table("qc_job") as batch:
        if "test_run_id" not in job_cols:
            batch.add_column(sa.Column("test_run_id", sa.Text(), nullable=True))
    _safe_create_index("idx_qc_job_test_run_id", "qc_job", ["test_run_id"])


def downgrade() -> None:
    with op.batch_alter_table("qc_job") as batch:
        try:
            batch.drop_column("test_run_id")
        except Exception:
            pass

    for t in (
        "qc_test_run",
        "qc_test_set_expected_finding",
        "qc_test_set_document",
        "qc_test_set",
    ):
        try:
            op.drop_table(t)
        except Exception:
            pass
