import hashlib
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext, resolve_actor_context
from app.core.config import get_settings
from app.db.session import get_db_session
from app.school_admissions.contracts import (
    contract_or_404,
    contract_read,
    contract_variables,
    render_contract,
    validate_template,
)
from app.school_admissions.document_storage import (
    InvalidEnrollmentDocumentError,
    save_enrollment_document,
)
from app.school_admissions.models import (
    ApplicationStatus,
    ClassCapacity,
    EnrollmentContract,
    EnrollmentContractAcceptance,
    EnrollmentContractStatus,
    EnrollmentContractTemplate,
    EnrollmentContractVersion,
    EnrollmentDocument,
    EnrollmentDocumentRequirement,
    EnrollmentDocumentReview,
    EnrollmentDocumentStatus,
    EnrollmentDocumentVersion,
    GuardianProfile,
    SchoolUnit,
    StudentEnrollmentApplication,
    StudentGuardianLink,
)
from app.school_admissions.policies import ensure_admissions_staff
from app.school_admissions.schemas import (
    AdmissionsDashboard,
    CapacitySnapshot,
    CapacityWrite,
    EnrollmentApplicationCreate,
    EnrollmentApplicationRead,
    EnrollmentApprovalRead,
    EnrollmentContractAccept,
    EnrollmentContractGenerate,
    EnrollmentContractRead,
    EnrollmentContractTemplateCreate,
    EnrollmentContractTemplateRead,
    EnrollmentContractVoid,
    EnrollmentDocumentChecklistItem,
    EnrollmentDocumentRead,
    EnrollmentDocumentRequirementCreate,
    EnrollmentDocumentRequirementRead,
    EnrollmentDocumentReviewWrite,
    EnrollmentGuardianOptionRead,
    SchoolUnitCreate,
    SchoolUnitRead,
    SeatDecisionRead,
)
from app.school_admissions.services import (
    application_or_404,
    application_read,
    approve_application,
    capacity_snapshot,
    classroom_or_404,
    create_application,
    document_requirement_or_404,
    enrollment_document_or_404,
    enrollment_document_read,
    reserve_or_waitlist,
    school_unit_or_404,
)
from app.services.object_storage import ObjectStorageError, storage_from_settings
from app.services.platform import append_audit_event

router = APIRouter(prefix="/school-admissions", tags=["Secretaria e matrículas"])


@router.get("/contract-templates", response_model=list[EnrollmentContractTemplateRead])
async def list_contract_templates(
    school_unit_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[EnrollmentContractTemplate]:
    await ensure_admissions_staff(session, actor, school_unit_id)
    statement = select(EnrollmentContractTemplate).where(
        EnrollmentContractTemplate.organization_id == actor.organization_id,
        EnrollmentContractTemplate.is_active.is_(True),
    )
    if school_unit_id:
        statement = statement.where(
            or_(
                EnrollmentContractTemplate.school_unit_id.is_(None),
                EnrollmentContractTemplate.school_unit_id == school_unit_id,
            )
        )
    return list((await session.scalars(statement.order_by(EnrollmentContractTemplate.name))).all())


@router.post("/contract-templates", response_model=EnrollmentContractTemplateRead, status_code=201)
async def create_contract_template(
    data: EnrollmentContractTemplateCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentContractTemplate:
    await ensure_admissions_staff(session, actor, data.school_unit_id)
    validate_template(data.body_template)
    if data.school_unit_id:
        await school_unit_or_404(session, actor.organization_id, data.school_unit_id)
    duplicate = await session.scalar(
        select(EnrollmentContractTemplate.id).where(
            EnrollmentContractTemplate.organization_id == actor.organization_id,
            EnrollmentContractTemplate.school_unit_id == data.school_unit_id,
            func.lower(EnrollmentContractTemplate.code) == data.code.casefold(),
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Código de template já utilizado")
    template = EnrollmentContractTemplate(
        organization_id=actor.organization_id,
        school_unit_id=data.school_unit_id,
        code=data.code,
        name=data.name.strip(),
        body_template=data.body_template.strip(),
        created_by_user_id=actor.user_id,
    )
    session.add(template)
    await session.flush()
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="enrollment_contract_template.created",
        entity_type="enrollment_contract_template",
        entity_id=template.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"code": template.code},
    )
    await session.commit()
    await session.refresh(template)
    return template


@router.get("/contracts", response_model=list[EnrollmentContractRead])
async def list_contracts(
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[EnrollmentContractRead]:
    await ensure_admissions_staff(session, actor)
    contracts = list(
        (
            await session.scalars(
                select(EnrollmentContract)
                .where(EnrollmentContract.organization_id == actor.organization_id)
                .order_by(EnrollmentContract.updated_at.desc())
            )
        ).all()
    )
    return [await contract_read(session, item) for item in contracts]


@router.get(
    "/applications/{application_id}/guardians",
    response_model=list[EnrollmentGuardianOptionRead],
)
async def list_application_guardians(
    application_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[GuardianProfile]:
    application = await application_or_404(session, actor.organization_id, application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    return list(
        (
            await session.scalars(
                select(GuardianProfile)
                .join(
                    StudentGuardianLink,
                    StudentGuardianLink.guardian_profile_id == GuardianProfile.id,
                )
                .where(
                    GuardianProfile.organization_id == actor.organization_id,
                    StudentGuardianLink.organization_id == actor.organization_id,
                    StudentGuardianLink.student_profile_id == application.student_profile_id,
                    GuardianProfile.is_active.is_(True),
                )
                .order_by(GuardianProfile.full_name)
            )
        ).all()
    )


@router.post("/applications/{application_id}/contract", response_model=EnrollmentContractRead)
async def generate_enrollment_contract(
    application_id: UUID,
    data: EnrollmentContractGenerate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentContractRead:
    application = await application_or_404(session, actor.organization_id, application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    template = await session.scalar(
        select(EnrollmentContractTemplate).where(
            EnrollmentContractTemplate.id == data.template_id,
            EnrollmentContractTemplate.organization_id == actor.organization_id,
            EnrollmentContractTemplate.is_active.is_(True),
            or_(
                EnrollmentContractTemplate.school_unit_id.is_(None),
                EnrollmentContractTemplate.school_unit_id == application.school_unit_id,
            ),
        )
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Template de contrato não encontrado")
    guardian, variables = await contract_variables(session, application, data.guardian_profile_id)
    variables["guardian_profile_id"] = str(guardian.id)
    rendered, content_hash = render_contract(template.body_template, variables)
    contract = await session.scalar(
        select(EnrollmentContract)
        .where(
            EnrollmentContract.organization_id == actor.organization_id,
            EnrollmentContract.application_id == application.id,
        )
        .with_for_update()
    )
    if contract and contract.status == EnrollmentContractStatus.ACCEPTED:
        raise HTTPException(status_code=409, detail="Contrato aceito não pode ser regenerado")
    if contract is None:
        contract = EnrollmentContract(
            organization_id=actor.organization_id,
            application_id=application.id,
            template_id=template.id,
            generated_by_user_id=actor.user_id,
            status=EnrollmentContractStatus.GENERATED,
            current_version_number=1,
        )
        session.add(contract)
        await session.flush()
        version_number = 1
    else:
        contract.template_id = template.id
        contract.status = EnrollmentContractStatus.GENERATED
        contract.void_reason = ""
        contract.voided_by_user_id = None
        contract.current_version_number += 1
        version_number = contract.current_version_number
    session.add(
        EnrollmentContractVersion(
            organization_id=actor.organization_id,
            contract_id=contract.id,
            version_number=version_number,
            template_snapshot=template.body_template,
            rendered_content=rendered,
            variables_snapshot=variables,
            content_sha256=content_hash,
            created_by_user_id=actor.user_id,
        )
    )
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="enrollment_contract.generated",
        entity_type="enrollment_contract",
        entity_id=contract.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"application_id": str(application.id), "version": version_number},
    )
    await session.commit()
    await session.refresh(contract)
    return await contract_read(session, contract)


@router.post("/contracts/{contract_id}/accept", response_model=EnrollmentContractRead)
async def accept_enrollment_contract(
    contract_id: UUID,
    data: EnrollmentContractAccept,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentContractRead:
    contract = await contract_or_404(session, actor.organization_id, contract_id, lock=True)
    if contract.status == EnrollmentContractStatus.ACCEPTED:
        return await contract_read(session, contract)
    if contract.status != EnrollmentContractStatus.GENERATED:
        raise HTTPException(status_code=409, detail="Contrato não está disponível para aceite")
    version = await session.scalar(
        select(EnrollmentContractVersion).where(
            EnrollmentContractVersion.organization_id == actor.organization_id,
            EnrollmentContractVersion.contract_id == contract.id,
            EnrollmentContractVersion.version_number == contract.current_version_number,
        )
    )
    guardian_id = (
        UUID(str(version.variables_snapshot.get("guardian_profile_id"))) if version else None
    )
    guardian = await session.scalar(
        select(GuardianProfile).where(
            GuardianProfile.id == guardian_id,
            GuardianProfile.organization_id == actor.organization_id,
            GuardianProfile.user_id == actor.user_id,
            GuardianProfile.is_active.is_(True),
        )
    )
    if guardian is None or data.accepted_name.strip().casefold() != guardian.full_name.casefold():
        raise HTTPException(
            status_code=403, detail="Aceite permitido apenas ao responsável identificado"
        )
    accepted_at = datetime.now(UTC)
    acceptance_hash = hashlib.sha256(
        f"{version.content_sha256}:{guardian.id}:{actor.user_id}:{accepted_at.isoformat()}".encode()
    ).hexdigest()
    session.add(
        EnrollmentContractAcceptance(
            organization_id=actor.organization_id,
            contract_id=contract.id,
            contract_version_id=version.id,
            guardian_profile_id=guardian.id,
            accepted_by_user_id=actor.user_id,
            accepted_name=guardian.full_name,
            acceptance_hash=acceptance_hash,
            ip_address=actor.ip_address,
            accepted_at=accepted_at,
        )
    )
    contract.status = EnrollmentContractStatus.ACCEPTED
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="enrollment_contract.accepted",
        entity_type="enrollment_contract",
        entity_id=contract.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"version": contract.current_version_number, "acceptance_hash": acceptance_hash},
    )
    await session.commit()
    await session.refresh(contract)
    return await contract_read(session, contract)


@router.post("/contracts/{contract_id}/void", response_model=EnrollmentContractRead)
async def void_enrollment_contract(
    contract_id: UUID,
    data: EnrollmentContractVoid,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentContractRead:
    contract = await contract_or_404(session, actor.organization_id, contract_id, lock=True)
    application = await application_or_404(session, actor.organization_id, contract.application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    if contract.status == EnrollmentContractStatus.ACCEPTED:
        raise HTTPException(
            status_code=409, detail="Contrato aceito exige processo formal de cancelamento"
        )
    contract.status = EnrollmentContractStatus.VOIDED
    contract.void_reason = data.reason.strip()
    contract.voided_by_user_id = actor.user_id
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="enrollment_contract.voided",
        entity_type="enrollment_contract",
        entity_id=contract.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"reason": contract.void_reason},
    )
    await session.commit()
    await session.refresh(contract)
    return await contract_read(session, contract)


@router.get("/document-requirements", response_model=list[EnrollmentDocumentRequirementRead])
async def list_document_requirements(
    school_unit_id: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[EnrollmentDocumentRequirement]:
    await ensure_admissions_staff(session, actor, school_unit_id)
    statement = select(EnrollmentDocumentRequirement).where(
        EnrollmentDocumentRequirement.organization_id == actor.organization_id,
        EnrollmentDocumentRequirement.is_active.is_(True),
    )
    if school_unit_id is not None:
        await school_unit_or_404(session, actor.organization_id, school_unit_id)
        statement = statement.where(
            or_(
                EnrollmentDocumentRequirement.school_unit_id.is_(None),
                EnrollmentDocumentRequirement.school_unit_id == school_unit_id,
            )
        )
    return list(
        (await session.scalars(statement.order_by(EnrollmentDocumentRequirement.name))).all()
    )


@router.post(
    "/document-requirements",
    response_model=EnrollmentDocumentRequirementRead,
    status_code=201,
)
async def create_document_requirement(
    data: EnrollmentDocumentRequirementCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentDocumentRequirement:
    await ensure_admissions_staff(session, actor, data.school_unit_id)
    if data.school_unit_id is not None:
        await school_unit_or_404(session, actor.organization_id, data.school_unit_id)
    duplicate = await session.scalar(
        select(EnrollmentDocumentRequirement.id).where(
            EnrollmentDocumentRequirement.organization_id == actor.organization_id,
            EnrollmentDocumentRequirement.school_unit_id == data.school_unit_id,
            func.lower(EnrollmentDocumentRequirement.code) == data.code.casefold(),
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Código de documento já configurado")
    requirement = EnrollmentDocumentRequirement(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        **data.model_dump(),
    )
    session.add(requirement)
    await session.flush()
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="enrollment_document_requirement.created",
        entity_type="enrollment_document_requirement",
        entity_id=requirement.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"code": requirement.code, "school_unit_id": str(data.school_unit_id or "")},
    )
    await session.commit()
    await session.refresh(requirement)
    return requirement


@router.get(
    "/applications/{application_id}/documents",
    response_model=list[EnrollmentDocumentChecklistItem],
)
async def application_document_checklist(
    application_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[EnrollmentDocumentChecklistItem]:
    application = await application_or_404(session, actor.organization_id, application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    requirements = list(
        (
            await session.scalars(
                select(EnrollmentDocumentRequirement)
                .where(
                    EnrollmentDocumentRequirement.organization_id == actor.organization_id,
                    EnrollmentDocumentRequirement.is_active.is_(True),
                    or_(
                        EnrollmentDocumentRequirement.school_unit_id.is_(None),
                        EnrollmentDocumentRequirement.school_unit_id == application.school_unit_id,
                    ),
                )
                .order_by(EnrollmentDocumentRequirement.name)
            )
        ).all()
    )
    documents = list(
        (
            await session.scalars(
                select(EnrollmentDocument).where(
                    EnrollmentDocument.organization_id == actor.organization_id,
                    EnrollmentDocument.application_id == application.id,
                )
            )
        ).all()
    )
    documents_by_requirement = {item.requirement_id: item for item in documents}
    return [
        EnrollmentDocumentChecklistItem(
            requirement=EnrollmentDocumentRequirementRead.model_validate(requirement),
            document=(
                await enrollment_document_read(session, documents_by_requirement[requirement.id])
                if requirement.id in documents_by_requirement
                else None
            ),
        )
        for requirement in requirements
    ]


@router.post(
    "/applications/{application_id}/documents",
    response_model=EnrollmentDocumentRead,
    status_code=201,
)
async def upload_application_document(
    application_id: UUID,
    requirement_id: UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentDocumentRead:
    application = await application_or_404(session, actor.organization_id, application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    requirement = await document_requirement_or_404(
        session, actor.organization_id, requirement_id, application.school_unit_id
    )
    document = await session.scalar(
        select(EnrollmentDocument)
        .where(
            EnrollmentDocument.organization_id == actor.organization_id,
            EnrollmentDocument.application_id == application.id,
            EnrollmentDocument.requirement_id == requirement.id,
        )
        .with_for_update()
    )
    if document is None:
        document = EnrollmentDocument(
            organization_id=actor.organization_id,
            application_id=application.id,
            requirement_id=requirement.id,
            status=EnrollmentDocumentStatus.SUBMITTED,
            current_version_number=1,
        )
        session.add(document)
        await session.flush()
        version_number = 1
    else:
        version_number = document.current_version_number + 1
        document.current_version_number = version_number
        document.status = EnrollmentDocumentStatus.SUBMITTED
        document.reviewed_by_user_id = None
        document.reviewed_at = None
        document.review_note = ""
        document.expires_at = None

    settings = get_settings()
    storage = storage_from_settings(settings)
    stored = None
    try:
        stored = await save_enrollment_document(
            storage,
            file,
            organization_id=actor.organization_id,
            application_id=application.id,
            document_id=document.id,
            version_number=version_number,
            accepted_mime_types=requirement.accepted_mime_types,
            max_size_bytes=min(
                requirement.max_size_bytes,
                settings.max_document_size_mb * 1024 * 1024,
            ),
        )
        version = EnrollmentDocumentVersion(
            organization_id=actor.organization_id,
            document_id=document.id,
            version_number=version_number,
            storage_key=stored.storage_key,
            original_filename=stored.original_filename,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            uploaded_by_user_id=actor.user_id,
        )
        session.add(version)
        await session.flush()
        await append_audit_event(
            session,
            organization_id=actor.organization_id,
            user_id=actor.user_id,
            module_name="school_admissions",
            action="enrollment_document.uploaded",
            entity_type="enrollment_document",
            entity_id=document.id,
            request_id=actor.request_id,
            ip_address=actor.ip_address,
            details={
                "requirement_id": str(requirement.id),
                "version": version_number,
                "checksum_sha256": stored.checksum_sha256,
            },
        )
        await session.commit()
    except InvalidEnrollmentDocumentError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ObjectStorageError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail="Armazenamento indisponível") from exc
    except Exception:
        await session.rollback()
        if stored is not None:
            await storage.delete(stored.storage_key)
        raise
    await session.refresh(document)
    return await enrollment_document_read(session, document)


@router.post("/documents/{document_id}/review", response_model=EnrollmentDocumentRead)
async def review_enrollment_document(
    document_id: UUID,
    data: EnrollmentDocumentReviewWrite,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentDocumentRead:
    document, application = await enrollment_document_or_404(
        session, actor.organization_id, document_id, lock=True
    )
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    version = await session.scalar(
        select(EnrollmentDocumentVersion).where(
            EnrollmentDocumentVersion.organization_id == actor.organization_id,
            EnrollmentDocumentVersion.document_id == document.id,
            EnrollmentDocumentVersion.version_number == document.current_version_number,
        )
    )
    if version is None:
        raise HTTPException(status_code=409, detail="Versão atual do documento não encontrada")
    document.status = data.decision
    document.reviewed_by_user_id = actor.user_id
    document.reviewed_at = datetime.now(UTC)
    document.review_note = data.note.strip()
    document.expires_at = data.expires_at
    session.add(
        EnrollmentDocumentReview(
            organization_id=actor.organization_id,
            document_id=document.id,
            document_version_id=version.id,
            decision=data.decision,
            note=data.note.strip(),
            reviewed_by_user_id=actor.user_id,
        )
    )
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action=f"enrollment_document.{data.decision}",
        entity_type="enrollment_document",
        entity_id=document.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"version": document.current_version_number},
    )
    await session.commit()
    await session.refresh(document)
    return await enrollment_document_read(session, document)


@router.get("/documents/{document_id}/versions/{version_id}/download")
async def download_enrollment_document(
    document_id: UUID,
    version_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> Response:
    document, application = await enrollment_document_or_404(
        session, actor.organization_id, document_id
    )
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    version = await session.scalar(
        select(EnrollmentDocumentVersion).where(
            EnrollmentDocumentVersion.id == version_id,
            EnrollmentDocumentVersion.organization_id == actor.organization_id,
            EnrollmentDocumentVersion.document_id == document.id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Versão do documento não encontrada")
    try:
        content = await storage_from_settings(get_settings()).get_bytes(version.storage_key)
    except ObjectStorageError as exc:
        raise HTTPException(status_code=404, detail="Arquivo privado não encontrado") from exc
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="enrollment_document.accessed",
        entity_type="enrollment_document",
        entity_id=document.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"version": version.version_number},
    )
    await session.commit()
    filename = quote(version.original_filename)
    return Response(
        content=content,
        media_type=version.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/units", response_model=list[SchoolUnitRead])
async def list_school_units(
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[SchoolUnit]:
    await ensure_admissions_staff(session, actor)
    return list(
        (
            await session.scalars(
                select(SchoolUnit)
                .where(SchoolUnit.organization_id == actor.organization_id)
                .order_by(SchoolUnit.name)
            )
        ).all()
    )


@router.post("/units", response_model=SchoolUnitRead, status_code=201)
async def create_school_unit(
    data: SchoolUnitCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> SchoolUnit:
    await ensure_admissions_staff(session, actor)
    if not actor.has_any_role("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Somente a administração cria unidades")
    duplicate = await session.scalar(
        select(SchoolUnit.id).where(
            SchoolUnit.organization_id == actor.organization_id,
            func.lower(SchoolUnit.code) == data.code.casefold(),
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Código de unidade já utilizado")
    unit = SchoolUnit(
        organization_id=actor.organization_id,
        name=data.name.strip(),
        code=data.code.strip().upper(),
        address=data.address,
    )
    session.add(unit)
    await session.flush()
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="school_unit.created",
        entity_type="school_unit",
        entity_id=unit.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"code": unit.code},
    )
    await session.commit()
    await session.refresh(unit)
    return unit


@router.put("/classrooms/{classroom_id}/capacity", response_model=CapacitySnapshot)
async def configure_capacity(
    classroom_id: UUID,
    data: CapacityWrite,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> CapacitySnapshot:
    classroom = await classroom_or_404(session, actor.organization_id, classroom_id)
    await ensure_admissions_staff(session, actor, classroom.school_unit_id)
    capacity = await session.scalar(
        select(ClassCapacity).where(
            ClassCapacity.organization_id == actor.organization_id,
            ClassCapacity.classroom_id == classroom.id,
        )
    )
    if capacity is None:
        capacity = ClassCapacity(
            organization_id=actor.organization_id,
            classroom_id=classroom.id,
            updated_by_user_id=actor.user_id,
            **data.model_dump(),
        )
        session.add(capacity)
    else:
        for field, value in data.model_dump().items():
            setattr(capacity, field, value)
        capacity.updated_by_user_id = actor.user_id
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="class_capacity.updated",
        entity_type="classroom",
        entity_id=classroom.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details=data.model_dump(),
    )
    await session.commit()
    return await capacity_snapshot(session, actor.organization_id, classroom.id)


@router.get("/classrooms/{classroom_id}/capacity", response_model=CapacitySnapshot)
async def get_capacity(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> CapacitySnapshot:
    classroom = await classroom_or_404(session, actor.organization_id, classroom_id)
    await ensure_admissions_staff(session, actor, classroom.school_unit_id)
    return await capacity_snapshot(session, actor.organization_id, classroom.id)


@router.post("/applications", response_model=EnrollmentApplicationRead, status_code=201)
async def submit_application(
    data: EnrollmentApplicationCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentApplicationRead:
    await school_unit_or_404(session, actor.organization_id, data.school_unit_id)
    await ensure_admissions_staff(session, actor, data.school_unit_id)
    application = await create_application(session, actor, data)
    return await application_read(session, application)


@router.get("/applications", response_model=list[EnrollmentApplicationRead])
async def list_applications(
    status: ApplicationStatus | None = None,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[EnrollmentApplicationRead]:
    await ensure_admissions_staff(session, actor)
    statement = select(StudentEnrollmentApplication).where(
        StudentEnrollmentApplication.organization_id == actor.organization_id
    )
    if status:
        statement = statement.where(StudentEnrollmentApplication.status == status)
    applications = (
        await session.scalars(statement.order_by(StudentEnrollmentApplication.created_at.desc()))
    ).all()
    return [await application_read(session, item) for item in applications]


@router.post(
    "/applications/{application_id}/reserve",
    response_model=SeatDecisionRead,
)
async def reserve_application_seat(
    application_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> SeatDecisionRead:
    application = await application_or_404(session, actor.organization_id, application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    outcome, expires_at, position, capacity = await reserve_or_waitlist(session, actor, application)
    return SeatDecisionRead(
        application_id=application.id,
        outcome=outcome,
        capacity=capacity,
        reservation_expires_at=expires_at,
        waitlist_position=position,
    )


@router.post(
    "/applications/{application_id}/approve",
    response_model=EnrollmentApprovalRead,
)
async def approve_enrollment_application(
    application_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentApprovalRead:
    application = await application_or_404(session, actor.organization_id, application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    enrollment, participant_created = await approve_application(session, actor, application)
    return EnrollmentApprovalRead(
        application_id=application.id,
        enrollment_id=enrollment.id,
        status=enrollment.status,
        classroom_participant_created=participant_created,
    )


@router.get("/dashboard", response_model=AdmissionsDashboard)
async def admissions_dashboard(
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> AdmissionsDashboard:
    await ensure_admissions_staff(session, actor)
    applications = list(
        (
            await session.scalars(
                select(StudentEnrollmentApplication)
                .where(StudentEnrollmentApplication.organization_id == actor.organization_id)
                .order_by(StudentEnrollmentApplication.created_at.desc())
                .limit(50)
            )
        ).all()
    )
    capacities = list(
        (
            await session.scalars(
                select(ClassCapacity).where(ClassCapacity.organization_id == actor.organization_id)
            )
        ).all()
    )
    counts = dict(
        (
            await session.execute(
                select(
                    StudentEnrollmentApplication.status,
                    func.count(StudentEnrollmentApplication.id),
                )
                .where(StudentEnrollmentApplication.organization_id == actor.organization_id)
                .group_by(StudentEnrollmentApplication.status)
            )
        ).all()
    )
    return AdmissionsDashboard(
        applications=[await application_read(session, item) for item in applications],
        capacities=[
            await capacity_snapshot(session, actor.organization_id, item.classroom_id)
            for item in capacities
        ],
        submitted=int(counts.get(ApplicationStatus.SUBMITTED, 0)),
        under_review=int(counts.get(ApplicationStatus.UNDER_REVIEW, 0)),
        waitlisted=int(counts.get(ApplicationStatus.WAITLISTED, 0)),
        approved=int(counts.get(ApplicationStatus.APPROVED, 0)),
    )
