"""Add QC tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-04 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "qc_template" not in existing_tables:
        op.create_table(
            "qc_template",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("model_id", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_template_user_id", "qc_template", ["user_id"])

    if "qc_job" not in existing_tables:
        op.create_table(
            "qc_job",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column(
                "template_id",
                sa.Text(),
                sa.ForeignKey("qc_template.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("overall_result", sa.Text(), nullable=True),
            sa.Column("model_id", sa.Text(), nullable=True),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_job_user_id", "qc_job", ["user_id"])
        op.create_index("idx_qc_job_template_id", "qc_job", ["template_id"])
        op.create_index("idx_qc_job_status", "qc_job", ["status"])

    if "qc_job_document" not in existing_tables:
        op.create_table(
            "qc_job_document",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column(
                "job_id",
                sa.Text(),
                sa.ForeignKey("qc_job.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "file_id",
                sa.Text(),
                sa.ForeignKey("file.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("document_type", sa.Text(), nullable=False, server_default="subject"),
            sa.Column("page_count", sa.Integer(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_job_document_job_id", "qc_job_document", ["job_id"])

    if "qc_finding" not in existing_tables:
        op.create_table(
            "qc_finding",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column(
                "job_id",
                sa.Text(),
                sa.ForeignKey("qc_job.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "document_id",
                sa.Text(),
                sa.ForeignKey("qc_job_document.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("source", sa.Text(), nullable=False, server_default="ai"),
            sa.Column("finding_number", sa.Integer(), nullable=True),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("checklist_item_id", sa.Text(), nullable=True),
            sa.Column("severity", sa.Text(), nullable=False, server_default="info"),
            sa.Column("status", sa.Text(), nullable=False, server_default="open"),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("location", sa.JSON(), nullable=True),
            sa.Column("ai_response", sa.JSON(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_finding_job_id", "qc_finding", ["job_id"])
        op.create_index("idx_qc_finding_document_id", "qc_finding", ["document_id"])
        op.create_index("idx_qc_finding_page_number", "qc_finding", ["job_id", "page_number"])
        op.create_index("idx_qc_finding_status", "qc_finding", ["status"])

    if "qc_comment" not in existing_tables:
        op.create_table(
            "qc_comment",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column(
                "finding_id",
                sa.Text(),
                sa.ForeignKey("qc_finding.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "job_id",
                sa.Text(),
                sa.ForeignKey("qc_job.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_qc_comment_finding_id", "qc_comment", ["finding_id"])
        op.create_index("idx_qc_comment_job_id", "qc_comment", ["job_id"])


def downgrade() -> None:
    op.drop_table("qc_comment")
    op.drop_table("qc_finding")
    op.drop_table("qc_job_document")
    op.drop_table("qc_job")
    op.drop_table("qc_template")
