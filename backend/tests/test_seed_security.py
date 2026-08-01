from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.db.seed import ensure_bootstrap_principal
from app.models.auth import Membership, Organization, OrganizationRole, User


def bootstrap_settings() -> Settings:
    return Settings(
        initial_organization_name="EduCode Enterprise",
        initial_organization_slug="educode-enterprise",
        initial_admin_email="admin@educode.com",
        initial_admin_name="Administrador EduCode",
        initial_admin_password="development-only-password",
    )


@pytest.mark.asyncio
async def test_seed_preserves_existing_revoked_principal():
    organization = Organization(
        id=uuid4(),
        name="EduCode Enterprise",
        slug="educode-enterprise",
        is_active=False,
    )
    user = User(
        id=uuid4(),
        email="admin@educode.com",
        full_name="Administradora revogada",
        hashed_password="hash",
        is_active=False,
        is_superuser=False,
    )
    membership = Membership(
        id=uuid4(),
        organization_id=organization.id,
        user_id=user.id,
        role=OrganizationRole.MEMBER,
        is_active=False,
    )
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[organization, user, membership]),
        add=Mock(),
        flush=AsyncMock(),
    )

    result_organization, result_user = await ensure_bootstrap_principal(
        session,
        bootstrap_settings(),
    )

    assert result_organization is organization
    assert result_user is user
    assert organization.is_active is False
    assert user.full_name == "Administradora revogada"
    assert user.is_active is False
    assert user.is_superuser is False
    assert membership.role == OrganizationRole.MEMBER
    assert membership.is_active is False
    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_does_not_restore_removed_membership_for_existing_user():
    organization = Organization(
        id=uuid4(),
        name="EduCode Enterprise",
        slug="educode-enterprise",
        is_active=True,
    )
    user = User(
        id=uuid4(),
        email="admin@educode.com",
        full_name="Administradora",
        hashed_password="hash",
        is_active=True,
        is_superuser=False,
    )
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[organization, user, None]),
        add=Mock(),
        flush=AsyncMock(),
    )

    await ensure_bootstrap_principal(session, bootstrap_settings())

    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_creates_owner_membership_only_with_new_initial_user():
    organization = Organization(
        id=uuid4(),
        name="EduCode Enterprise",
        slug="educode-enterprise",
        is_active=True,
    )
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[organization, None, None]),
        add=Mock(),
        flush=AsyncMock(),
    )

    await ensure_bootstrap_principal(session, bootstrap_settings())

    added = [call.args[0] for call in session.add.call_args_list]
    user = next(item for item in added if isinstance(item, User))
    membership = next(item for item in added if isinstance(item, Membership))
    assert user.is_superuser is True
    assert user.is_active is True
    assert membership.role == OrganizationRole.OWNER
    assert membership.is_active is True
