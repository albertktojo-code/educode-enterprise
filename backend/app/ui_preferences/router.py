from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import (
    ActorContext,
    get_project_session,
    resolve_actor_context,
)
from app.models.auth import User
from app.services.consolidated_audit import append_domain_audit

from .schemas import InterfacePreferenceUpsert


router = APIRouter(
    prefix="/ui-preferences",
    tags=["ui-preferences"],
)
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

DEFAULTS: dict[str, Any] = {
    "sidebar_mode": "expanded",
    "sidebar_width": 260,
    "editor_focus_default": False,
    "reduce_motion": False,
    "last_open_section": "",
}


def normalize(value: dict[str, Any] | None) -> dict[str, Any]:
    data = {**DEFAULTS, **(value or {})}
    mode = str(data.get("sidebar_mode", "expanded"))
    if mode not in {"expanded", "compact", "hidden", "auto"}:
        mode = "expanded"
    width = int(data.get("sidebar_width", 260))
    width = 64 if mode == "compact" else max(210, min(340, width))
    return {
        "sidebar_mode": mode,
        "sidebar_width": width,
        "editor_focus_default": bool(
            data.get("editor_focus_default", False)
        ),
        "reduce_motion": bool(data.get("reduce_motion", False)),
        "last_open_section": str(
            data.get("last_open_section", "")
        )[:120],
    }


@router.get("/me")
async def get_preferences(
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    user = await session.scalar(
        select(User).where(User.id == actor.user_id)
    )
    if user is None:
        raise HTTPException(404, "Usuário não encontrado.")
    return normalize(user.ui_preferences)


@router.put("/me")
async def save_preferences(
    data: InterfacePreferenceUpsert,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    user = await session.scalar(
        select(User)
        .where(User.id == actor.user_id)
        .with_for_update()
    )
    if user is None:
        raise HTTPException(404, "Usuário não encontrado.")
    preferences = normalize(data.model_dump())
    user.ui_preferences = {
        **(user.ui_preferences or {}),
        **preferences,
    }
    await append_domain_audit(
        session,
        actor=actor,
        module_name="ui_preferences",
        action="ui.preferences.updated",
        entity_type="user",
        entity_id=actor.user_id,
        details=preferences,
    )
    await session.commit()
    return preferences
