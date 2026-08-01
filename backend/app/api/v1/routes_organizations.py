import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, Organization, OrganizationRole
from app.schemas.auth import OrganizationRead, OrganizationUpdate

router = APIRouter(prefix="/organization", tags=["Organização"])

read_access = require_roles(
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
    OrganizationRole.MEMBER,
)
write_access = require_roles(OrganizationRole.OWNER, OrganizationRole.ADMIN)


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if len(slug) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Slug inválido",
        )
    return slug


@router.get("", response_model=OrganizationRead)
async def get_organization(
    membership: Membership = Depends(read_access),
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    organization = await session.get(Organization, membership.organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    return organization


@router.patch("", response_model=OrganizationRead)
async def update_organization(
    data: OrganizationUpdate,
    membership: Membership = Depends(write_access),
    session: AsyncSession = Depends(get_db_session),
) -> Organization:
    organization = await session.get(Organization, membership.organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organização não encontrada")

    if data.name is not None:
        organization.name = data.name.strip()

    if data.slug is not None:
        slug = normalize_slug(data.slug)
        existing = await session.scalar(
            select(Organization).where(
                Organization.slug == slug,
                Organization.id != organization.id,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este identificador já está em uso",
            )
        organization.slug = slug

    await session.commit()
    await session.refresh(organization)
    return organization
