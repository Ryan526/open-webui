"""Add QC template versioning

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-16 12:00:00.000000

"""

import json
import time
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
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


def _safe_create_index(name: str, table: str, cols: list, unique: bool = False) -> None:
    from sqlalchemy import Inspector

    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    try:
        existing = {ix["name"] for ix in inspector.get_indexes(table)}
    except Exception:
        existing = set()
    if name not in existing:
        op.create_index(name, table, cols, unique=unique)


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "qc_template_version" not in existing_tables:
        op.create_table(
            "qc_template_version",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True),
            sa.Column("template_id", sa.Text(), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("parent_version_id", sa.Text(), nullable=True),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("model_id", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("change_summary", sa.Text(), nullable=True),
            sa.Column("change_source", sa.Text(), nullable=False, server_default="manual"),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "idx_qc_template_version_template_id",
            "qc_template_version",
            ["template_id"],
        )
        op.create_index(
            "uq_qc_template_version_template_id_number",
            "qc_template_version",
            ["template_id", "version_number"],
            unique=True,
        )

    # Add current_version_id to qc_template
    tmpl_cols = _column_names("qc_template")
    with op.batch_alter_table("qc_template") as batch:
        if "current_version_id" not in tmpl_cols:
            batch.add_column(sa.Column("current_version_id", sa.Text(), nullable=True))

    # Add template_version_id to qc_job
    job_cols = _column_names("qc_job")
    with op.batch_alter_table("qc_job") as batch:
        if "template_version_id" not in job_cols:
            batch.add_column(sa.Column("template_version_id", sa.Text(), nullable=True))
    _safe_create_index(
        "idx_qc_job_template_version_id",
        "qc_job",
        ["template_version_id"],
    )

    # Backfill: create an "initial" version per existing template and pin current_version_id
    bind = op.get_bind()
    templates = list(
        bind.execute(
            sa.text(
                "SELECT id, user_id, name, description, system_prompt, model_id, meta, "
                "current_version_id, updated_at FROM qc_template"
            )
        )
    )

    for row in templates:
        t_id = row[0]
        t_user_id = row[1]
        t_name = row[2]
        t_desc = row[3]
        t_sp = row[4]
        t_model = row[5]
        t_meta_raw = row[6]
        current_version_id = row[7]
        t_updated_at = row[8]

        if current_version_id:
            # Already has a current version — skip backfill
            continue

        # Check if a version already exists for this template (idempotency)
        existing_v = bind.execute(
            sa.text(
                "SELECT id FROM qc_template_version WHERE template_id = :tid ORDER BY version_number DESC LIMIT 1"
            ),
            {"tid": t_id},
        ).fetchone()
        if existing_v:
            # Pin current_version_id to the latest existing version
            bind.execute(
                sa.text(
                    "UPDATE qc_template SET current_version_id = :vid WHERE id = :tid"
                ),
                {"vid": existing_v[0], "tid": t_id},
            )
            continue

        # Create v1 'initial'
        version_id = str(uuid.uuid4())
        meta_json = t_meta_raw
        if isinstance(meta_json, (dict, list)):
            meta_json = json.dumps(meta_json)
        now = int(t_updated_at or time.time())
        bind.execute(
            sa.text(
                "INSERT INTO qc_template_version "
                "(id, template_id, version_number, user_id, parent_version_id, "
                " name, description, system_prompt, model_id, meta, change_summary, "
                " change_source, created_at) "
                "VALUES (:id, :tid, 1, :uid, NULL, :n, :d, :sp, :m, :meta, "
                " :summary, 'initial', :ca)"
            ),
            {
                "id": version_id,
                "tid": t_id,
                "uid": t_user_id,
                "n": t_name,
                "d": t_desc,
                "sp": t_sp,
                "m": t_model,
                "meta": meta_json,
                "summary": "Initial version (backfilled)",
                "ca": now,
            },
        )
        bind.execute(
            sa.text(
                "UPDATE qc_template SET current_version_id = :vid WHERE id = :tid"
            ),
            {"vid": version_id, "tid": t_id},
        )


def downgrade() -> None:
    existing_tables = set(get_existing_tables())

    with op.batch_alter_table("qc_job") as batch:
        try:
            batch.drop_column("template_version_id")
        except Exception:
            pass
    with op.batch_alter_table("qc_template") as batch:
        try:
            batch.drop_column("current_version_id")
        except Exception:
            pass
    if "qc_template_version" in existing_tables:
        op.drop_table("qc_template_version")
