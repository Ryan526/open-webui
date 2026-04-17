import logging
import time
from typing import Optional
import uuid

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context

from open_webui.models.access_grants import AccessGrantModel, AccessGrants

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)

log = logging.getLogger(__name__)

####################
# QC Project DB Schema
####################


class QCProject(Base):
    __tablename__ = "qc_project"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text, nullable=True)

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCProjectModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: Optional[str] = None

    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class QCProjectForm(BaseModel):
    name: str
    description: Optional[str] = None
    meta: Optional[dict] = None


####################
# QC Template DB Schema
####################


class QCTemplate(Base):
    __tablename__ = "qc_template"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text, nullable=True)

    system_prompt = Column(Text, nullable=True)
    model_id = Column(Text, nullable=True)

    meta = Column(JSON, nullable=True)

    current_version_id = Column(Text, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCTemplateModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    model_id: Optional[str] = None

    meta: Optional[dict] = None

    current_version_id: Optional[str] = None

    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    created_at: int
    updated_at: int


class QCTemplateForm(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: Optional[str] = None
    meta: Optional[dict] = None
    access_grants: Optional[list[dict]] = None


####################
# QC Job DB Schema
####################


class QCJob(Base):
    __tablename__ = "qc_job"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)
    template_id = Column(
        Text, ForeignKey("qc_template.id", ondelete="SET NULL"), nullable=True
    )

    name = Column(Text)
    status = Column(Text, default="pending")  # pending|running|completed|failed
    overall_result = Column(Text, nullable=True)  # pass|fail|flagged|null

    model_id = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)

    project_id = Column(
        Text, ForeignKey("qc_project.id", ondelete="SET NULL"), nullable=True
    )
    previous_job_id = Column(
        Text, ForeignKey("qc_job.id", ondelete="SET NULL"), nullable=True
    )
    revision_label = Column(Text, nullable=True)
    revision_index = Column(Integer, nullable=True)

    template_version_id = Column(Text, nullable=True)
    test_run_id = Column(Text, nullable=True)

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCJobModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    template_id: Optional[str] = None

    name: str
    status: str = "pending"
    overall_result: Optional[str] = None

    model_id: Optional[str] = None
    system_prompt: Optional[str] = None

    project_id: Optional[str] = None
    previous_job_id: Optional[str] = None
    revision_label: Optional[str] = None
    revision_index: Optional[int] = None

    template_version_id: Optional[str] = None
    test_run_id: Optional[str] = None

    meta: Optional[dict] = None

    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    created_at: int
    updated_at: int


class QCJobForm(BaseModel):
    name: str
    template_id: Optional[str] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None
    project_id: Optional[str] = None
    previous_job_id: Optional[str] = None
    revision_label: Optional[str] = None
    template_version_id: Optional[str] = None
    test_run_id: Optional[str] = None
    meta: Optional[dict] = None
    access_grants: Optional[list[dict]] = None


####################
# QC Job Document DB Schema
####################


class QCJobDocument(Base):
    __tablename__ = "qc_job_document"

    id = Column(Text, unique=True, primary_key=True)
    job_id = Column(
        Text, ForeignKey("qc_job.id", ondelete="CASCADE"), nullable=False
    )
    file_id = Column(
        Text, ForeignKey("file.id", ondelete="CASCADE"), nullable=False
    )

    document_type = Column(Text, default="subject")  # subject|reference
    page_count = Column(Integer, nullable=True)
    status = Column(Text, default="pending")  # pending|processing|completed|failed

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCJobDocumentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    file_id: str

    document_type: str = "subject"
    page_count: Optional[int] = None
    status: str = "pending"

    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class QCJobDocumentForm(BaseModel):
    file_id: str
    document_type: str = "subject"


####################
# QC Finding DB Schema
####################


class QCFinding(Base):
    __tablename__ = "qc_finding"

    id = Column(Text, unique=True, primary_key=True)
    job_id = Column(
        Text, ForeignKey("qc_job.id", ondelete="CASCADE"), nullable=False
    )
    document_id = Column(
        Text, ForeignKey("qc_job_document.id", ondelete="CASCADE"), nullable=True
    )
    user_id = Column(Text)

    source = Column(Text, default="ai")  # ai|human
    finding_number = Column(Integer, nullable=True)
    page_number = Column(Integer, nullable=True)
    checklist_item_id = Column(Text, nullable=True)

    severity = Column(Text, default="info")  # critical|major|minor|info
    status = Column(Text, default="open")  # open|confirmed|dismissed|resolved

    title = Column(Text)
    description = Column(Text, nullable=True)

    location = Column(JSON, nullable=True)  # {x, y, width, height} normalized 0-1
    ai_response = Column(JSON, nullable=True)

    previous_finding_id = Column(
        Text, ForeignKey("qc_finding.id", ondelete="SET NULL"), nullable=True
    )
    revision_state = Column(Text, nullable=True)  # new|carried_over|resolved

    canonical_finding_id = Column(
        Text, ForeignKey("qc_finding.id", ondelete="SET NULL"), nullable=True
    )
    dup_cluster_key = Column(Text, nullable=True)

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCFindingModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    document_id: Optional[str] = None
    user_id: str

    source: str = "ai"
    finding_number: Optional[int] = None
    page_number: Optional[int] = None
    checklist_item_id: Optional[str] = None

    severity: str = "info"
    status: str = "open"

    title: str
    description: Optional[str] = None

    location: Optional[dict | list] = None
    ai_response: Optional[dict] = None

    previous_finding_id: Optional[str] = None
    revision_state: Optional[str] = None

    canonical_finding_id: Optional[str] = None
    dup_cluster_key: Optional[str] = None

    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class QCFindingForm(BaseModel):
    document_id: Optional[str] = None
    source: str = "human"
    page_number: Optional[int] = None
    checklist_item_id: Optional[str] = None
    severity: str = "info"
    title: str
    description: Optional[str] = None
    location: Optional[dict] = None
    meta: Optional[dict] = None


class QCFindingUpdateForm(BaseModel):
    severity: Optional[str] = None
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[dict | list] = None
    meta: Optional[dict] = None


####################
# QC Comment DB Schema
####################


class QCComment(Base):
    __tablename__ = "qc_comment"

    id = Column(Text, unique=True, primary_key=True)
    finding_id = Column(
        Text, ForeignKey("qc_finding.id", ondelete="CASCADE"), nullable=False
    )
    job_id = Column(
        Text, ForeignKey("qc_job.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Text)

    content = Column(Text)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCCommentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    job_id: str
    user_id: str

    content: str
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class QCCommentForm(BaseModel):
    content: str
    meta: Optional[dict] = None


####################
# QC Report DB Schema
####################


class QCReport(Base):
    __tablename__ = "qc_report"

    id = Column(Text, unique=True, primary_key=True)
    job_id = Column(
        Text, ForeignKey("qc_job.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Text)

    report_type = Column(Text)  # branded_pdf|redlined_pdf|json|csv
    file_id = Column(
        Text, ForeignKey("file.id", ondelete="SET NULL"), nullable=True
    )
    status = Column(Text, default="pending")  # pending|generating|ready|failed
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCReportModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    user_id: str

    report_type: str
    file_id: Optional[str] = None
    status: str = "pending"
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class QCReportForm(BaseModel):
    report_type: str  # branded_pdf|redlined_pdf|json|csv
    meta: Optional[dict] = None


####################
# QC Projects Table (CRUD)
####################


class QCProjectsTable:
    def insert_new_project(
        self,
        user_id: str,
        form_data: QCProjectForm,
        db: Optional[Session] = None,
    ) -> Optional[QCProjectModel]:
        with get_db_context(db) as db:
            project = QCProjectModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCProject(**project.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return QCProjectModel.model_validate(result)

    def get_projects(
        self,
        user_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> list[QCProjectModel]:
        with get_db_context(db) as db:
            query = db.query(QCProject)
            if user_id:
                query = query.filter_by(user_id=user_id)
            projects = query.order_by(QCProject.updated_at.desc()).all()
            return [QCProjectModel.model_validate(p) for p in projects]

    def get_project_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCProjectModel]:
        with get_db_context(db) as db:
            project = db.query(QCProject).filter_by(id=id).first()
            return QCProjectModel.model_validate(project) if project else None

    def update_project_by_id(
        self,
        id: str,
        form_data: QCProjectForm,
        db: Optional[Session] = None,
    ) -> Optional[QCProjectModel]:
        with get_db_context(db) as db:
            db.query(QCProject).filter_by(id=id).update(
                {
                    **form_data.model_dump(),
                    "updated_at": int(time.time()),
                }
            )
            db.commit()
            return self.get_project_by_id(id=id, db=db)

    def delete_project_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            db.query(QCProject).filter_by(id=id).delete()
            db.commit()
            return True

    def get_jobs_by_project_id(
        self, project_id: str, db: Optional[Session] = None
    ) -> list[QCJobModel]:
        with get_db_context(db) as db:
            jobs = (
                db.query(QCJob)
                .filter_by(project_id=project_id)
                .order_by(
                    QCJob.revision_index.asc(),
                    QCJob.created_at.asc(),
                )
                .all()
            )
            grants_map = AccessGrants.get_grants_by_resources(
                "qc_job", [j.id for j in jobs], db=db
            )
            models: list[QCJobModel] = []
            for j in jobs:
                m = QCJobModel.model_validate(j)
                m.access_grants = grants_map.get(j.id, [])
                models.append(m)
            return models


####################
# QC Template Version DB Schema
####################


# Content-affecting fields for version diffing
_VERSIONED_META_KEYS = (
    "checklist",
    "knowledge_base_ids",
    "cross_reference_analysis",
    "vision_settings",
)


class QCTemplateVersion(Base):
    __tablename__ = "qc_template_version"

    id = Column(Text, unique=True, primary_key=True)
    template_id = Column(Text)
    version_number = Column(Integer)
    user_id = Column(Text)

    parent_version_id = Column(Text, nullable=True)

    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    model_id = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)

    change_summary = Column(Text, nullable=True)
    change_source = Column(Text, default="manual")  # manual|self_improve|restore|initial

    created_at = Column(BigInteger)


class QCTemplateVersionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template_id: str
    version_number: int
    user_id: str

    parent_version_id: Optional[str] = None

    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: Optional[str] = None
    meta: Optional[dict] = None

    change_summary: Optional[str] = None
    change_source: str = "manual"

    created_at: int


####################
# QC Template Versions Table (CRUD)
####################


class QCTemplateVersionsTable:
    def get_next_version_number(
        self, template_id: str, db: Optional[Session] = None
    ) -> int:
        with get_db_context(db) as db:
            row = (
                db.query(QCTemplateVersion.version_number)
                .filter_by(template_id=template_id)
                .order_by(QCTemplateVersion.version_number.desc())
                .first()
            )
            return (row[0] or 0) + 1 if row and row[0] else 1

    def create_version(
        self,
        template_id: str,
        user_id: str,
        name: Optional[str],
        description: Optional[str],
        system_prompt: Optional[str],
        model_id: Optional[str],
        meta: Optional[dict],
        change_summary: Optional[str] = None,
        change_source: str = "manual",
        parent_version_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[QCTemplateVersionModel]:
        with get_db_context(db) as db:
            version_number = self.get_next_version_number(template_id, db=db)
            row = QCTemplateVersion(
                id=str(uuid.uuid4()),
                template_id=template_id,
                version_number=version_number,
                user_id=user_id,
                parent_version_id=parent_version_id,
                name=name,
                description=description,
                system_prompt=system_prompt,
                model_id=model_id,
                meta=meta,
                change_summary=change_summary,
                change_source=change_source,
                created_at=int(time.time()),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return QCTemplateVersionModel.model_validate(row)

    def get_versions_by_template_id(
        self, template_id: str, db: Optional[Session] = None
    ) -> list[QCTemplateVersionModel]:
        with get_db_context(db) as db:
            rows = (
                db.query(QCTemplateVersion)
                .filter_by(template_id=template_id)
                .order_by(QCTemplateVersion.version_number.desc())
                .all()
            )
            return [QCTemplateVersionModel.model_validate(r) for r in rows]

    def get_version_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCTemplateVersionModel]:
        with get_db_context(db) as db:
            row = db.query(QCTemplateVersion).filter_by(id=id).first()
            return QCTemplateVersionModel.model_validate(row) if row else None

    def get_version_by_number(
        self,
        template_id: str,
        version_number: int,
        db: Optional[Session] = None,
    ) -> Optional[QCTemplateVersionModel]:
        with get_db_context(db) as db:
            row = (
                db.query(QCTemplateVersion)
                .filter_by(template_id=template_id, version_number=version_number)
                .first()
            )
            return QCTemplateVersionModel.model_validate(row) if row else None


def _content_fields_changed(old: QCTemplateModel, new_form: "QCTemplateForm") -> bool:
    """Return True if any content-affecting field differs between the live template and the incoming form.

    Content-affecting fields: system_prompt, model_id, and the content keys of meta
    (checklist, knowledge_base_ids, cross_reference_analysis, vision_settings).
    Name + description are intentionally excluded per the plan.
    """
    if (old.system_prompt or None) != (new_form.system_prompt or None):
        return True
    if (old.model_id or None) != (new_form.model_id or None):
        return True
    old_meta = old.meta or {}
    new_meta = new_form.meta or {}
    for key in _VERSIONED_META_KEYS:
        if old_meta.get(key) != new_meta.get(key):
            return True
    return False


####################
# QC Templates Table (CRUD)
####################


class QCTemplatesTable:
    def _to_model(
        self,
        template: QCTemplate,
        db: Optional[Session] = None,
        grants: Optional[list[AccessGrantModel]] = None,
    ) -> Optional[QCTemplateModel]:
        if not template:
            return None
        model = QCTemplateModel.model_validate(template)
        if grants is not None:
            model.access_grants = grants
        else:
            model.access_grants = AccessGrants.get_grants_by_resource(
                "qc_template", template.id, db=db
            )
        return model

    def insert_new_template(
        self,
        user_id: str,
        form_data: QCTemplateForm,
        db: Optional[Session] = None,
    ) -> Optional[QCTemplateModel]:
        with get_db_context(db) as db:
            template = QCTemplateModel(
                **{
                    **form_data.model_dump(exclude={"access_grants"}),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "access_grants": [],
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCTemplate(
                **template.model_dump(exclude={"access_grants"})
            )
            db.add(result)
            db.commit()
            db.refresh(result)

            # Auto-create v1 "initial" and pin it as current_version_id
            initial = QCTemplateVersions.create_version(
                template_id=result.id,
                user_id=user_id,
                name=result.name,
                description=result.description,
                system_prompt=result.system_prompt,
                model_id=result.model_id,
                meta=result.meta,
                change_summary="Initial version",
                change_source="initial",
                db=db,
            )
            if initial:
                result.current_version_id = initial.id
                db.commit()
                db.refresh(result)

            if form_data.access_grants is not None:
                AccessGrants.set_access_grants(
                    "qc_template", result.id, form_data.access_grants, db=db
                )

            return self._to_model(result, db=db)

    def get_templates(
        self, db: Optional[Session] = None
    ) -> list[QCTemplateModel]:
        with get_db_context(db) as db:
            templates = (
                db.query(QCTemplate)
                .order_by(QCTemplate.updated_at.desc())
                .all()
            )
            grants_map = AccessGrants.get_grants_by_resources(
                "qc_template", [t.id for t in templates], db=db
            )
            return [
                self._to_model(t, db=db, grants=grants_map.get(t.id, []))
                for t in templates
            ]

    def get_template_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCTemplateModel]:
        with get_db_context(db) as db:
            template = db.query(QCTemplate).filter_by(id=id).first()
            return self._to_model(template, db=db)

    def update_template_by_id(
        self,
        id: str,
        form_data: QCTemplateForm,
        db: Optional[Session] = None,
        change_source: str = "manual",
        change_summary: Optional[str] = None,
        actor_user_id: Optional[str] = None,
    ) -> Optional[QCTemplateModel]:
        with get_db_context(db) as db:
            current = self.get_template_by_id(id=id, db=db)
            if not current:
                return None

            content_changed = _content_fields_changed(current, form_data)

            data = form_data.model_dump(exclude={"access_grants"})
            db.query(QCTemplate).filter_by(id=id).update(
                {
                    **data,
                    "updated_at": int(time.time()),
                }
            )
            db.commit()

            if content_changed:
                new_version = QCTemplateVersions.create_version(
                    template_id=id,
                    user_id=actor_user_id or current.user_id,
                    name=form_data.name,
                    description=form_data.description,
                    system_prompt=form_data.system_prompt,
                    model_id=form_data.model_id,
                    meta=form_data.meta,
                    change_summary=change_summary,
                    change_source=change_source,
                    parent_version_id=current.current_version_id,
                    db=db,
                )
                if new_version:
                    db.query(QCTemplate).filter_by(id=id).update(
                        {"current_version_id": new_version.id}
                    )
                    db.commit()

            if form_data.access_grants is not None:
                AccessGrants.set_access_grants(
                    "qc_template", id, form_data.access_grants, db=db
                )

            return self.get_template_by_id(id=id, db=db)

    def delete_template_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            AccessGrants.revoke_all_access("qc_template", id, db=db)
            db.query(QCTemplate).filter_by(id=id).delete()
            db.commit()
            return True


####################
# QC Jobs Table (CRUD)
####################


class QCJobsTable:
    def _to_model(
        self,
        job: QCJob,
        db: Optional[Session] = None,
        grants: Optional[list[AccessGrantModel]] = None,
    ) -> Optional[QCJobModel]:
        if not job:
            return None
        model = QCJobModel.model_validate(job)
        if grants is not None:
            model.access_grants = grants
        else:
            model.access_grants = AccessGrants.get_grants_by_resource(
                "qc_job", job.id, db=db
            )
        return model

    def insert_new_job(
        self,
        user_id: str,
        form_data: QCJobForm,
        db: Optional[Session] = None,
    ) -> Optional[QCJobModel]:
        with get_db_context(db) as db:
            data = form_data.model_dump(exclude={"access_grants"})

            # Auto-compute revision_index and inherit project_id if linked
            previous_job_id = data.get("previous_job_id")
            revision_index: Optional[int] = None
            if previous_job_id:
                prev = db.query(QCJob).filter_by(id=previous_job_id).first()
                if prev:
                    prev_index = prev.revision_index if prev.revision_index is not None else 0
                    revision_index = prev_index + 1
                    # Inherit project_id if not explicitly set
                    if not data.get("project_id") and prev.project_id:
                        data["project_id"] = prev.project_id

            job = QCJobModel(
                **{
                    **data,
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "status": "pending",
                    "overall_result": None,
                    "revision_index": revision_index,
                    "access_grants": [],
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCJob(**job.model_dump(exclude={"access_grants"}))
            db.add(result)
            db.commit()
            db.refresh(result)

            if form_data.access_grants is not None:
                AccessGrants.set_access_grants(
                    "qc_job", result.id, form_data.access_grants, db=db
                )

            return self._to_model(result, db=db)

    def get_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> list[QCJobModel]:
        with get_db_context(db) as db:
            query = db.query(QCJob)
            if user_id:
                query = query.filter_by(user_id=user_id)
            if status:
                query = query.filter_by(status=status)
            jobs = query.order_by(QCJob.updated_at.desc()).all()
            grants_map = AccessGrants.get_grants_by_resources(
                "qc_job", [j.id for j in jobs], db=db
            )
            return [
                self._to_model(j, db=db, grants=grants_map.get(j.id, []))
                for j in jobs
            ]

    def get_job_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCJobModel]:
        with get_db_context(db) as db:
            job = db.query(QCJob).filter_by(id=id).first()
            return self._to_model(job, db=db)

    def update_job_by_id(
        self,
        id: str,
        form_data: QCJobForm,
        db: Optional[Session] = None,
    ) -> Optional[QCJobModel]:
        with get_db_context(db) as db:
            db.query(QCJob).filter_by(id=id).update(
                {
                    **form_data.model_dump(exclude={"access_grants"}),
                    "updated_at": int(time.time()),
                }
            )
            db.commit()

            if form_data.access_grants is not None:
                AccessGrants.set_access_grants(
                    "qc_job", id, form_data.access_grants, db=db
                )

            return self.get_job_by_id(id=id, db=db)

    def update_job_status(
        self,
        id: str,
        status: str,
        overall_result: Optional[str] = None,
        meta: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> Optional[QCJobModel]:
        with get_db_context(db) as db:
            update_data = {
                "status": status,
                "updated_at": int(time.time()),
            }
            if overall_result is not None:
                update_data["overall_result"] = overall_result
            if meta is not None:
                update_data["meta"] = meta
            db.query(QCJob).filter_by(id=id).update(update_data)
            db.commit()
            return self.get_job_by_id(id=id, db=db)

    def delete_job_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            AccessGrants.revoke_all_access("qc_job", id, db=db)
            db.query(QCJob).filter_by(id=id).delete()
            db.commit()
            return True


####################
# QC Job Documents Table (CRUD)
####################


class QCJobDocumentsTable:
    def insert_document(
        self,
        job_id: str,
        form_data: QCJobDocumentForm,
        db: Optional[Session] = None,
    ) -> Optional[QCJobDocumentModel]:
        with get_db_context(db) as db:
            doc = QCJobDocumentModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "job_id": job_id,
                    "page_count": None,
                    "status": "pending",
                    "meta": None,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCJobDocument(**doc.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return QCJobDocumentModel.model_validate(result)

    def get_documents_by_job_id(
        self, job_id: str, db: Optional[Session] = None
    ) -> list[QCJobDocumentModel]:
        with get_db_context(db) as db:
            docs = (
                db.query(QCJobDocument)
                .filter_by(job_id=job_id)
                .order_by(QCJobDocument.created_at.asc())
                .all()
            )
            return [QCJobDocumentModel.model_validate(d) for d in docs]

    def get_document_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCJobDocumentModel]:
        with get_db_context(db) as db:
            doc = db.query(QCJobDocument).filter_by(id=id).first()
            return QCJobDocumentModel.model_validate(doc) if doc else None

    def update_document(
        self,
        id: str,
        page_count: Optional[int] = None,
        status: Optional[str] = None,
        meta: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> Optional[QCJobDocumentModel]:
        with get_db_context(db) as db:
            update_data = {"updated_at": int(time.time())}
            if page_count is not None:
                update_data["page_count"] = page_count
            if status is not None:
                update_data["status"] = status
            if meta is not None:
                update_data["meta"] = meta
            db.query(QCJobDocument).filter_by(id=id).update(update_data)
            db.commit()
            return self.get_document_by_id(id=id, db=db)

    def delete_document(
        self, id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            db.query(QCJobDocument).filter_by(id=id).delete()
            db.commit()
            return True


####################
# QC Findings Table (CRUD)
####################


class QCFindingsTable:
    def insert_finding(
        self,
        user_id: str,
        job_id: str,
        form_data: QCFindingForm,
        db: Optional[Session] = None,
    ) -> Optional[QCFindingModel]:
        with get_db_context(db) as db:
            # Auto-assign finding_number
            max_num = (
                db.query(QCFinding.finding_number)
                .filter_by(job_id=job_id)
                .order_by(QCFinding.finding_number.desc())
                .first()
            )
            next_num = (max_num[0] or 0) + 1 if max_num and max_num[0] else 1

            finding = QCFindingModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "job_id": job_id,
                    "user_id": user_id,
                    "finding_number": next_num,
                    "status": "open",
                    "ai_response": None,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCFinding(**finding.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return QCFindingModel.model_validate(result)

    def insert_finding_raw(
        self,
        finding_data: dict,
        db: Optional[Session] = None,
    ) -> Optional[QCFindingModel]:
        """Insert a finding with all fields pre-set (used by AI analysis)."""
        with get_db_context(db) as db:
            result = QCFinding(**finding_data)
            db.add(result)
            db.commit()
            db.refresh(result)
            return QCFindingModel.model_validate(result)

    def get_findings_by_job_id(
        self,
        job_id: str,
        page_number: Optional[int] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        document_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> list[QCFindingModel]:
        with get_db_context(db) as db:
            query = db.query(QCFinding).filter_by(job_id=job_id)
            if page_number is not None:
                query = query.filter_by(page_number=page_number)
            if severity:
                query = query.filter_by(severity=severity)
            if status:
                query = query.filter_by(status=status)
            if document_id:
                query = query.filter_by(document_id=document_id)
            findings = query.order_by(QCFinding.finding_number.asc()).all()
            return [QCFindingModel.model_validate(f) for f in findings]

    def get_finding_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCFindingModel]:
        with get_db_context(db) as db:
            finding = db.query(QCFinding).filter_by(id=id).first()
            return QCFindingModel.model_validate(finding) if finding else None

    def update_finding(
        self,
        id: str,
        form_data: QCFindingUpdateForm,
        db: Optional[Session] = None,
    ) -> Optional[QCFindingModel]:
        with get_db_context(db) as db:
            update_data = {
                k: v
                for k, v in form_data.model_dump().items()
                if v is not None
            }
            update_data["updated_at"] = int(time.time())
            db.query(QCFinding).filter_by(id=id).update(update_data)
            db.commit()
            return self.get_finding_by_id(id=id, db=db)

    def delete_finding(
        self, id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            db.query(QCFinding).filter_by(id=id).delete()
            db.commit()
            return True

    def delete_findings_by_job_id(
        self, job_id: str, db: Optional[Session] = None
    ) -> int:
        """Delete all findings for a job. Returns count of deleted rows."""
        with get_db_context(db) as db:
            count = db.query(QCFinding).filter_by(job_id=job_id).delete()
            db.commit()
            return count

    def get_next_finding_number(
        self, job_id: str, db: Optional[Session] = None
    ) -> int:
        with get_db_context(db) as db:
            max_num = (
                db.query(QCFinding.finding_number)
                .filter_by(job_id=job_id)
                .order_by(QCFinding.finding_number.desc())
                .first()
            )
            return (max_num[0] or 0) + 1 if max_num and max_num[0] else 1

    def bulk_update_fields(
        self,
        job_id: str,
        finding_ids: list[str],
        updates: dict,
        db: Optional[Session] = None,
    ) -> int:
        """Apply a flat field update to many findings at once. Returns rows updated."""
        if not finding_ids or not updates:
            return 0
        with get_db_context(db) as db:
            update_data = {k: v for k, v in updates.items() if v is not None}
            update_data["updated_at"] = int(time.time())
            count = (
                db.query(QCFinding)
                .filter(QCFinding.job_id == job_id, QCFinding.id.in_(finding_ids))
                .update(update_data, synchronize_session=False)
            )
            db.commit()
            return count

    def set_canonical(
        self,
        finding_id: str,
        canonical_id: Optional[str],
        db: Optional[Session] = None,
    ) -> None:
        with get_db_context(db) as db:
            db.query(QCFinding).filter_by(id=finding_id).update(
                {"canonical_finding_id": canonical_id, "updated_at": int(time.time())},
                synchronize_session=False,
            )
            db.commit()

    def get_findings_in_job_by_page_doc(
        self,
        job_id: str,
        document_id: str,
        page_number: int,
        db: Optional[Session] = None,
    ) -> list[QCFindingModel]:
        with get_db_context(db) as db:
            rows = (
                db.query(QCFinding)
                .filter_by(job_id=job_id, document_id=document_id, page_number=page_number)
                .all()
            )
            return [QCFindingModel.model_validate(r) for r in rows]


####################
# QC Comments Table (CRUD)
####################


class QCCommentsTable:
    def insert_comment(
        self,
        user_id: str,
        finding_id: str,
        job_id: str,
        form_data: QCCommentForm,
        db: Optional[Session] = None,
    ) -> Optional[QCCommentModel]:
        with get_db_context(db) as db:
            comment = QCCommentModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "finding_id": finding_id,
                    "job_id": job_id,
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCComment(**comment.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return QCCommentModel.model_validate(result)

    def get_comments_by_finding_id(
        self, finding_id: str, db: Optional[Session] = None
    ) -> list[QCCommentModel]:
        with get_db_context(db) as db:
            comments = (
                db.query(QCComment)
                .filter_by(finding_id=finding_id)
                .order_by(QCComment.created_at.asc())
                .all()
            )
            return [QCCommentModel.model_validate(c) for c in comments]

    def get_comment_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCCommentModel]:
        with get_db_context(db) as db:
            comment = db.query(QCComment).filter_by(id=id).first()
            return QCCommentModel.model_validate(comment) if comment else None

    def update_comment(
        self,
        id: str,
        content: str,
        db: Optional[Session] = None,
    ) -> Optional[QCCommentModel]:
        with get_db_context(db) as db:
            db.query(QCComment).filter_by(id=id).update(
                {"content": content, "updated_at": int(time.time())}
            )
            db.commit()
            return self.get_comment_by_id(id=id, db=db)

    def delete_comment(
        self, id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            db.query(QCComment).filter_by(id=id).delete()
            db.commit()
            return True


####################
# QC Suppression DB Schema
####################


class QCSuppressionRule(Base):
    __tablename__ = "qc_suppression_rule"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    scope = Column(Text)  # template|project|global
    template_id = Column(Text, nullable=True)
    project_id = Column(Text, nullable=True)

    name = Column(Text)
    enabled = Column(Integer, default=1)

    match_type = Column(Text)  # title_exact|title_regex|title_contains|checklist_item
    match_value = Column(Text)
    severity_filter = Column(Text, nullable=True)
    page_tag_filter = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)

    hit_count = Column(Integer, default=0)
    last_hit_at = Column(BigInteger, nullable=True)

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCSuppressionRuleModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    scope: str
    template_id: Optional[str] = None
    project_id: Optional[str] = None

    name: str
    enabled: int = 1

    match_type: str
    match_value: str
    severity_filter: Optional[str] = None
    page_tag_filter: Optional[str] = None
    reason: Optional[str] = None

    hit_count: int = 0
    last_hit_at: Optional[int] = None

    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class QCSuppressionRuleForm(BaseModel):
    scope: str  # template|project|global
    template_id: Optional[str] = None
    project_id: Optional[str] = None
    name: str
    enabled: Optional[int] = 1
    match_type: str
    match_value: str
    severity_filter: Optional[str] = None
    page_tag_filter: Optional[str] = None
    reason: Optional[str] = None
    meta: Optional[dict] = None


class QCSuppressionEvent(Base):
    __tablename__ = "qc_suppression_event"

    id = Column(Text, unique=True, primary_key=True)
    rule_id = Column(
        Text, ForeignKey("qc_suppression_rule.id", ondelete="CASCADE"), nullable=False
    )
    job_id = Column(
        Text, ForeignKey("qc_job.id", ondelete="CASCADE"), nullable=False
    )
    document_id = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    suppressed_title = Column(Text, nullable=True)
    suppressed_payload = Column(JSON, nullable=True)

    created_at = Column(BigInteger)


class QCSuppressionEventModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_id: str
    job_id: str
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    suppressed_title: Optional[str] = None
    suppressed_payload: Optional[dict] = None

    created_at: int


####################
# QC Suppression Rules Table (CRUD)
####################


class QCSuppressionRulesTable:
    def insert_rule(
        self,
        user_id: str,
        form_data: QCSuppressionRuleForm,
        db: Optional[Session] = None,
    ) -> Optional[QCSuppressionRuleModel]:
        with get_db_context(db) as db:
            rule = QCSuppressionRuleModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "hit_count": 0,
                    "last_hit_at": None,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCSuppressionRule(**rule.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return QCSuppressionRuleModel.model_validate(result)

    def get_rules(
        self,
        user_id: Optional[str] = None,
        scope: Optional[str] = None,
        template_id: Optional[str] = None,
        project_id: Optional[str] = None,
        enabled_only: bool = False,
        db: Optional[Session] = None,
    ) -> list[QCSuppressionRuleModel]:
        with get_db_context(db) as db:
            query = db.query(QCSuppressionRule)
            if user_id:
                query = query.filter_by(user_id=user_id)
            if scope:
                query = query.filter_by(scope=scope)
            if template_id:
                query = query.filter_by(template_id=template_id)
            if project_id:
                query = query.filter_by(project_id=project_id)
            if enabled_only:
                query = query.filter_by(enabled=1)
            rules = query.order_by(QCSuppressionRule.updated_at.desc()).all()
            return [QCSuppressionRuleModel.model_validate(r) for r in rules]

    def get_rule_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCSuppressionRuleModel]:
        with get_db_context(db) as db:
            rule = db.query(QCSuppressionRule).filter_by(id=id).first()
            return QCSuppressionRuleModel.model_validate(rule) if rule else None

    def update_rule(
        self,
        id: str,
        form_data: QCSuppressionRuleForm,
        db: Optional[Session] = None,
    ) -> Optional[QCSuppressionRuleModel]:
        with get_db_context(db) as db:
            db.query(QCSuppressionRule).filter_by(id=id).update(
                {**form_data.model_dump(), "updated_at": int(time.time())}
            )
            db.commit()
            return self.get_rule_by_id(id=id, db=db)

    def delete_rule(self, id: str, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            db.query(QCSuppressionRule).filter_by(id=id).delete()
            db.commit()
            return True

    def record_hit(
        self, id: str, db: Optional[Session] = None
    ) -> None:
        with get_db_context(db) as db:
            now = int(time.time())
            row = db.query(QCSuppressionRule).filter_by(id=id).first()
            if not row:
                return
            row.hit_count = int(row.hit_count or 0) + 1
            row.last_hit_at = now
            row.updated_at = now
            db.commit()


####################
# QC Suppression Events Table (CRUD)
####################


class QCSuppressionEventsTable:
    def insert_event(
        self,
        rule_id: str,
        job_id: str,
        document_id: Optional[str],
        page_number: Optional[int],
        suppressed_title: Optional[str],
        suppressed_payload: Optional[dict],
        db: Optional[Session] = None,
    ) -> Optional[QCSuppressionEventModel]:
        with get_db_context(db) as db:
            row = QCSuppressionEvent(
                id=str(uuid.uuid4()),
                rule_id=rule_id,
                job_id=job_id,
                document_id=document_id,
                page_number=page_number,
                suppressed_title=suppressed_title,
                suppressed_payload=suppressed_payload,
                created_at=int(time.time()),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return QCSuppressionEventModel.model_validate(row)

    def get_events_by_job_id(
        self, job_id: str, db: Optional[Session] = None
    ) -> list[QCSuppressionEventModel]:
        with get_db_context(db) as db:
            events = (
                db.query(QCSuppressionEvent)
                .filter_by(job_id=job_id)
                .order_by(QCSuppressionEvent.created_at.desc())
                .all()
            )
            return [QCSuppressionEventModel.model_validate(e) for e in events]


####################
# QC Reports Table (CRUD)
####################


class QCReportsTable:
    def insert_report(
        self,
        user_id: str,
        job_id: str,
        form_data: QCReportForm,
        db: Optional[Session] = None,
    ) -> Optional[QCReportModel]:
        with get_db_context(db) as db:
            report = QCReportModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "job_id": job_id,
                    "user_id": user_id,
                    "status": "pending",
                    "file_id": None,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCReport(**report.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return QCReportModel.model_validate(result)

    def get_reports_by_job_id(
        self, job_id: str, db: Optional[Session] = None
    ) -> list[QCReportModel]:
        with get_db_context(db) as db:
            reports = (
                db.query(QCReport)
                .filter_by(job_id=job_id)
                .order_by(QCReport.created_at.desc())
                .all()
            )
            return [QCReportModel.model_validate(r) for r in reports]

    def get_report_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCReportModel]:
        with get_db_context(db) as db:
            report = db.query(QCReport).filter_by(id=id).first()
            return QCReportModel.model_validate(report) if report else None

    def update_report(
        self,
        id: str,
        status: Optional[str] = None,
        file_id: Optional[str] = None,
        meta: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> Optional[QCReportModel]:
        with get_db_context(db) as db:
            update_data: dict = {"updated_at": int(time.time())}
            if status is not None:
                update_data["status"] = status
            if file_id is not None:
                update_data["file_id"] = file_id
            if meta is not None:
                update_data["meta"] = meta
            db.query(QCReport).filter_by(id=id).update(update_data)
            db.commit()
            return self.get_report_by_id(id=id, db=db)

    def delete_report(
        self, id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            db.query(QCReport).filter_by(id=id).delete()
            db.commit()
            return True


####################
# QC Test Harness DB Schema
####################


class QCTestSet(Base):
    __tablename__ = "qc_test_set"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)
    name = Column(Text)
    description = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCTestSetModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int


class QCTestSetForm(BaseModel):
    name: str
    description: Optional[str] = None
    meta: Optional[dict] = None


class QCTestSetDocument(Base):
    __tablename__ = "qc_test_set_document"

    id = Column(Text, unique=True, primary_key=True)
    test_set_id = Column(
        Text, ForeignKey("qc_test_set.id", ondelete="CASCADE"), nullable=False
    )
    file_id = Column(
        Text, ForeignKey("file.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(BigInteger)


class QCTestSetDocumentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    test_set_id: str
    file_id: str
    name: Optional[str] = None
    page_count: Optional[int] = None
    meta: Optional[dict] = None
    created_at: int


class QCTestSetExpectedFinding(Base):
    __tablename__ = "qc_test_set_expected_finding"

    id = Column(Text, unique=True, primary_key=True)
    test_set_id = Column(
        Text, ForeignKey("qc_test_set.id", ondelete="CASCADE"), nullable=False
    )
    document_id = Column(
        Text,
        ForeignKey("qc_test_set_document.id", ondelete="CASCADE"),
        nullable=False,
    )

    page_number = Column(Integer, nullable=True)
    checklist_item_id = Column(Text, nullable=True)
    severity = Column(Text, nullable=True)
    title = Column(Text)
    description = Column(Text, nullable=True)
    location = Column(JSON, nullable=True)
    match_title_patterns = Column(JSON, nullable=True)
    seeded_from_finding_id = Column(Text, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCTestSetExpectedFindingModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    test_set_id: str
    document_id: str

    page_number: Optional[int] = None
    checklist_item_id: Optional[str] = None
    severity: Optional[str] = None
    title: str
    description: Optional[str] = None
    location: Optional[dict] = None
    match_title_patterns: Optional[list] = None
    seeded_from_finding_id: Optional[str] = None

    created_at: int
    updated_at: int


class QCTestSetExpectedFindingForm(BaseModel):
    document_id: str
    page_number: Optional[int] = None
    checklist_item_id: Optional[str] = None
    severity: Optional[str] = None
    title: str
    description: Optional[str] = None
    location: Optional[dict] = None
    match_title_patterns: Optional[list] = None
    seeded_from_finding_id: Optional[str] = None


class QCTestRun(Base):
    __tablename__ = "qc_test_run"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)
    test_set_id = Column(
        Text, ForeignKey("qc_test_set.id", ondelete="CASCADE"), nullable=False
    )
    template_id = Column(Text, nullable=True)
    template_version_id = Column(Text, nullable=True)

    status = Column(Text, default="pending")  # pending|running|completed|failed
    shadow_job_id = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class QCTestRunModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    test_set_id: str
    template_id: Optional[str] = None
    template_version_id: Optional[str] = None

    status: str = "pending"
    shadow_job_id: Optional[str] = None
    metrics: Optional[dict] = None
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


####################
# QC Test Sets Table (CRUD)
####################


class QCTestSetsTable:
    def insert_test_set(
        self,
        user_id: str,
        form_data: QCTestSetForm,
        db: Optional[Session] = None,
    ) -> Optional[QCTestSetModel]:
        with get_db_context(db) as db:
            row = QCTestSetModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = QCTestSet(**row.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return QCTestSetModel.model_validate(result)

    def get_test_sets(
        self, user_id: Optional[str] = None, db: Optional[Session] = None
    ) -> list[QCTestSetModel]:
        with get_db_context(db) as db:
            q = db.query(QCTestSet)
            if user_id:
                q = q.filter_by(user_id=user_id)
            rows = q.order_by(QCTestSet.updated_at.desc()).all()
            return [QCTestSetModel.model_validate(r) for r in rows]

    def get_test_set_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCTestSetModel]:
        with get_db_context(db) as db:
            row = db.query(QCTestSet).filter_by(id=id).first()
            return QCTestSetModel.model_validate(row) if row else None

    def update_test_set(
        self,
        id: str,
        form_data: QCTestSetForm,
        db: Optional[Session] = None,
    ) -> Optional[QCTestSetModel]:
        with get_db_context(db) as db:
            db.query(QCTestSet).filter_by(id=id).update(
                {**form_data.model_dump(), "updated_at": int(time.time())}
            )
            db.commit()
            return self.get_test_set_by_id(id=id, db=db)

    def delete_test_set(self, id: str, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            db.query(QCTestSet).filter_by(id=id).delete()
            db.commit()
            return True


class QCTestSetDocumentsTable:
    def insert_document(
        self,
        test_set_id: str,
        file_id: str,
        name: Optional[str] = None,
        page_count: Optional[int] = None,
        meta: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> Optional[QCTestSetDocumentModel]:
        with get_db_context(db) as db:
            row = QCTestSetDocument(
                id=str(uuid.uuid4()),
                test_set_id=test_set_id,
                file_id=file_id,
                name=name,
                page_count=page_count,
                meta=meta,
                created_at=int(time.time()),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return QCTestSetDocumentModel.model_validate(row)

    def get_documents_by_test_set_id(
        self, test_set_id: str, db: Optional[Session] = None
    ) -> list[QCTestSetDocumentModel]:
        with get_db_context(db) as db:
            rows = (
                db.query(QCTestSetDocument)
                .filter_by(test_set_id=test_set_id)
                .order_by(QCTestSetDocument.created_at.asc())
                .all()
            )
            return [QCTestSetDocumentModel.model_validate(r) for r in rows]

    def get_document_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCTestSetDocumentModel]:
        with get_db_context(db) as db:
            row = db.query(QCTestSetDocument).filter_by(id=id).first()
            return QCTestSetDocumentModel.model_validate(row) if row else None

    def delete_document(self, id: str, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            db.query(QCTestSetDocument).filter_by(id=id).delete()
            db.commit()
            return True


class QCTestSetExpectedFindingsTable:
    def insert_expected(
        self,
        test_set_id: str,
        form_data: QCTestSetExpectedFindingForm,
        db: Optional[Session] = None,
    ) -> Optional[QCTestSetExpectedFindingModel]:
        with get_db_context(db) as db:
            row = QCTestSetExpectedFindingModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "test_set_id": test_set_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            db_row = QCTestSetExpectedFinding(**row.model_dump())
            db.add(db_row)
            db.commit()
            db.refresh(db_row)
            return QCTestSetExpectedFindingModel.model_validate(db_row)

    def get_expected_by_test_set_id(
        self, test_set_id: str, db: Optional[Session] = None
    ) -> list[QCTestSetExpectedFindingModel]:
        with get_db_context(db) as db:
            rows = (
                db.query(QCTestSetExpectedFinding)
                .filter_by(test_set_id=test_set_id)
                .order_by(QCTestSetExpectedFinding.created_at.asc())
                .all()
            )
            return [QCTestSetExpectedFindingModel.model_validate(r) for r in rows]

    def update_expected(
        self,
        id: str,
        form_data: QCTestSetExpectedFindingForm,
        db: Optional[Session] = None,
    ) -> Optional[QCTestSetExpectedFindingModel]:
        with get_db_context(db) as db:
            db.query(QCTestSetExpectedFinding).filter_by(id=id).update(
                {**form_data.model_dump(), "updated_at": int(time.time())}
            )
            db.commit()
            row = db.query(QCTestSetExpectedFinding).filter_by(id=id).first()
            return QCTestSetExpectedFindingModel.model_validate(row) if row else None

    def delete_expected(self, id: str, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            db.query(QCTestSetExpectedFinding).filter_by(id=id).delete()
            db.commit()
            return True


class QCTestRunsTable:
    def insert_run(
        self,
        user_id: str,
        test_set_id: str,
        template_id: Optional[str] = None,
        template_version_id: Optional[str] = None,
        meta: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> Optional[QCTestRunModel]:
        with get_db_context(db) as db:
            row = QCTestRun(
                id=str(uuid.uuid4()),
                user_id=user_id,
                test_set_id=test_set_id,
                template_id=template_id,
                template_version_id=template_version_id,
                status="pending",
                shadow_job_id=None,
                metrics=None,
                meta=meta,
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return QCTestRunModel.model_validate(row)

    def update_run(
        self,
        id: str,
        status: Optional[str] = None,
        shadow_job_id: Optional[str] = None,
        metrics: Optional[dict] = None,
        meta: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> Optional[QCTestRunModel]:
        with get_db_context(db) as db:
            data: dict = {"updated_at": int(time.time())}
            if status is not None:
                data["status"] = status
            if shadow_job_id is not None:
                data["shadow_job_id"] = shadow_job_id
            if metrics is not None:
                data["metrics"] = metrics
            if meta is not None:
                data["meta"] = meta
            db.query(QCTestRun).filter_by(id=id).update(data)
            db.commit()
            row = db.query(QCTestRun).filter_by(id=id).first()
            return QCTestRunModel.model_validate(row) if row else None

    def get_runs(
        self,
        user_id: Optional[str] = None,
        test_set_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> list[QCTestRunModel]:
        with get_db_context(db) as db:
            q = db.query(QCTestRun)
            if user_id:
                q = q.filter_by(user_id=user_id)
            if test_set_id:
                q = q.filter_by(test_set_id=test_set_id)
            rows = q.order_by(QCTestRun.created_at.desc()).all()
            return [QCTestRunModel.model_validate(r) for r in rows]

    def get_run_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[QCTestRunModel]:
        with get_db_context(db) as db:
            row = db.query(QCTestRun).filter_by(id=id).first()
            return QCTestRunModel.model_validate(row) if row else None


# Singleton instances
QCProjects = QCProjectsTable()
QCTemplateVersions = QCTemplateVersionsTable()
QCTemplates = QCTemplatesTable()
QCJobs = QCJobsTable()
QCJobDocuments = QCJobDocumentsTable()
QCFindings = QCFindingsTable()
QCComments = QCCommentsTable()
QCReports = QCReportsTable()
QCSuppressionRules = QCSuppressionRulesTable()
QCSuppressionEvents = QCSuppressionEventsTable()
QCTestSets = QCTestSetsTable()
QCTestSetDocuments = QCTestSetDocumentsTable()
QCTestSetExpectedFindings = QCTestSetExpectedFindingsTable()
QCTestRuns = QCTestRunsTable()
