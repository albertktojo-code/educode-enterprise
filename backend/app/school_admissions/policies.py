from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext
from app.models.platform import FeatureFlag
from app.school_admissions.models import InstitutionalStaffAssignment

ADMISSIONS_FLAG = "SCHOOL_ADMISSIONS_ENABLED"
ADMISSIONS_STAFF_ROLES = ("secretariat", "coordinator")


async def ensure_admissions_enabled(session: AsyncSession, actor: ActorContext) -> None:
    if actor.has_any_role("OWNER", "ADMIN"):
        return
    flag = await session.scalar(
        select(FeatureFlag).where(
            FeatureFlag.organization_id == actor.organization_id,
            FeatureFlag.flag_key == ADMISSIONS_FLAG,
            FeatureFlag.scope_type == "organization",
            FeatureFlag.scope_id.is_(None),
        )
    )
    if flag is None or not flag.is_enabled:
        raise HTTPException(status_code=404, detail="Módulo de matrículas não habilitado")


async def ensure_admissions_staff(
    session: AsyncSession,
    actor: ActorContext,
    school_unit_id: UUID | None = None,
) -> None:
    await ensure_admissions_enabled(session, actor)
    if actor.has_any_role("OWNER", "ADMIN"):
        return
    assignment = await session.scalar(
        select(InstitutionalStaffAssignment.id).where(
            InstitutionalStaffAssignment.organization_id == actor.organization_id,
            InstitutionalStaffAssignment.membership_id == actor.membership_id,
            InstitutionalStaffAssignment.staff_role.in_(ADMISSIONS_STAFF_ROLES),
            InstitutionalStaffAssignment.is_active.is_(True),
            or_(
                InstitutionalStaffAssignment.school_unit_id.is_(None),
                InstitutionalStaffAssignment.school_unit_id == school_unit_id,
            ),
        )
    )
    if assignment is None:
        raise HTTPException(status_code=403, detail="Acesso à Secretaria não autorizado")
