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

    meta: Optional[dict] = None

    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    created_at: int
    updated_at: int


class QCJobForm(BaseModel):
    name: str
    template_id: Optional[str] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None
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
# QC Templates Table (CRUD)
####################


class QCTemplatesTable:
    def _to_model(
        self, template: QCTemplate, db: Optional[Session] = None
    ) -> Optional[QCTemplateModel]:
        if not template:
            return None
        model = QCTemplateModel.model_validate(template)
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
            return [self._to_model(t, db=db) for t in templates]

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
    ) -> Optional[QCTemplateModel]:
        with get_db_context(db) as db:
            db.query(QCTemplate).filter_by(id=id).update(
                {
                    **form_data.model_dump(exclude={"access_grants"}),
                    "updated_at": int(time.time()),
                }
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
        self, job: QCJob, db: Optional[Session] = None
    ) -> Optional[QCJobModel]:
        if not job:
            return None
        model = QCJobModel.model_validate(job)
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
            job = QCJobModel(
                **{
                    **form_data.model_dump(exclude={"access_grants"}),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "status": "pending",
                    "overall_result": None,
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
            return [self._to_model(j, db=db) for j in jobs]

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


# Singleton instances
QCTemplates = QCTemplatesTable()
QCJobs = QCJobsTable()
QCJobDocuments = QCJobDocumentsTable()
QCFindings = QCFindingsTable()
QCComments = QCCommentsTable()
