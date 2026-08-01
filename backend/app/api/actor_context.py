from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.api.dependencies import get_current_user
from app.db.base import Base
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User

# Mantem a assinatura esperada pelos modulos incrementais.
get_project_session = get_db_session


@dataclass(frozen=True, slots=True)
class ActorContext:
    user_id: UUID
    organization_id: UUID
    membership_id: UUID
    roles: frozenset[str]
    is_superuser: bool = False
    request_id: str = ""
    ip_address: str = ""

    def has_any_role(self, *roles: str) -> bool:
        expected = {role.upper() for role in roles}
        return bool(self.roles.intersection(expected))


_ROLE_ALIASES: dict[OrganizationRole, set[str]] = {
    OrganizationRole.OWNER: {
        "OWNER",
        "ADMIN",
        "ORG_ADMIN",
        "PLATFORM_ADMIN",
        "COORDINATOR",
        "PEDAGOGICAL_COORDINATOR",
        "EDITOR",
        "REVIEWER",
    },
    OrganizationRole.ADMIN: {
        "ADMIN",
        "ORG_ADMIN",
        "COORDINATOR",
        "PEDAGOGICAL_COORDINATOR",
        "EDITOR",
        "REVIEWER",
    },
    OrganizationRole.TEACHER: {
        "TEACHER",
        "EDITOR",
        "REVIEWER",
        "PEDAGOGICAL_REVIEWER",
    },
    OrganizationRole.MEMBER: {
        "MEMBER",
        "STUDENT",
        "LEARNER",
    },
}


def role_aliases(role: OrganizationRole, *, is_superuser: bool = False) -> frozenset[str]:
    roles = {role.value.upper(), role.name.upper(), *_ROLE_ALIASES.get(role, set())}
    if is_superuser:
        roles.update({"SUPERUSER", "PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"})
    return frozenset(roles)


def _active_memberships(user: User) -> list[Membership]:
    return [
        membership
        for membership in user.memberships
        if membership.is_active and membership.organization.is_active
    ]


def _select_membership(
    user: User,
    requested_organization: str | None,
) -> Membership:
    active = _active_memberships(user)
    if not active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_CONTEXT_REQUIRED",
                "message": "Usuario autenticado sem organizacao ativa.",
            },
        )

    if not requested_organization:
        return active[0]

    try:
        organization_id = UUID(requested_organization)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_ORGANIZATION_HEADER",
                "message": "X-Organization-ID deve conter um UUID valido.",
            },
        ) from exc

    membership = next(
        (item for item in active if item.organization_id == organization_id),
        None,
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "O usuario nao pertence a organizacao solicitada.",
            },
        )
    return membership


async def resolve_actor_context(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ActorContext:
    membership = _select_membership(
        current_user,
        request.headers.get("X-Organization-ID"),
    )
    client_host = request.client.host if request.client else ""
    return ActorContext(
        user_id=current_user.id,
        organization_id=membership.organization_id,
        membership_id=membership.id,
        roles=role_aliases(membership.role, is_superuser=current_user.is_superuser),
        is_superuser=current_user.is_superuser,
        request_id=getattr(request.state, "request_id", ""),
        ip_address=client_host,
    )


__all__ = [
    "ActorContext",
    "Base",
    "get_project_session",
    "resolve_actor_context",
    "role_aliases",
]
