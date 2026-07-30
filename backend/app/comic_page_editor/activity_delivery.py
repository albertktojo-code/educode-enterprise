from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.assessment_delivery.access import canonical_target_type
if TYPE_CHECKING:
    from .compat import ActorContext

async def create_delivery(session: AsyncSession, *, actor: ActorContext, project_id: uuid.UUID, data: Any):
    from . import models
    from app.assessment_delivery.models import AssessmentPublication, AssessmentTarget
    activities=list((await session.scalars(select(models.HQActivityBinding).where(
        models.HQActivityBinding.organization_id==actor.organization_id,
        models.HQActivityBinding.comic_project_id==project_id,
        models.HQActivityBinding.status=="APPROVED",
    ).order_by(models.HQActivityBinding.display_order))).all())
    if not activities:
        raise HTTPException(409,"A HQ não possui atividades aprovadas.")
    publication=AssessmentPublication(
        organization_id=actor.organization_id,
        code=f"HQ-{str(project_id)[:8]}-{uuid.uuid4().hex[:6]}".upper(),
        title=data.title,
        version=1,
        source_type="HQ_ACTIVITY_SET",
        source_id=project_id,
        item_snapshot=[{
            "activity_binding_id":str(item.id),
            "question_version_id":str(item.question_version_id),
            "title":item.title,
            "activity_type":item.activity_type,
            "max_score":item.max_score,
        } for item in activities],
        status="DRAFT",
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        duration_minutes=data.duration_minutes,
        max_attempts=data.max_attempts,
        navigation_mode=data.navigation_mode,
        shuffle_questions=data.shuffle_questions,
        shuffle_options=data.shuffle_options,
        allow_resume=data.allow_resume,
        autosave_seconds=data.autosave_seconds,
        delivery_rules={
            "reader_required":data.reader_required,
            "release_answer_key":data.release_answer_key,
            "comic_project_id":str(project_id),
        },
        access_settings=data.access_settings,
        created_by_user_id=actor.user_id,
    )
    session.add(publication); await session.flush()
    for target in data.targets:
        session.add(AssessmentTarget(
            organization_id=actor.organization_id,
            publication_id=publication.id,
            target_type=canonical_target_type(target.target_type),
            target_id=target.target_id,
            available_from=target.available_from,
            available_until=target.available_until,
            extra_attempts=target.extra_attempts,
            custom_duration_minutes=target.custom_duration_minutes,
            status="ACTIVE",
            assigned_by_user_id=actor.user_id,
        ))
    link=models.HQActivityDeliveryLink(
        organization_id=actor.organization_id,
        comic_project_id=project_id,
        publication_id=publication.id,
        delivery_mode=data.delivery_mode,
        reader_required=data.reader_required,
        release_answer_key=data.release_answer_key,
        monitoring_settings=data.monitoring_settings,
        status="SCHEDULED",
        created_by_user_id=actor.user_id,
    )
    session.add(link)
    for item in activities:
        item.publication_id=publication.id
    await session.flush()
    return link,publication

async def publish_delivery(session:AsyncSession,*,actor:ActorContext,link_id:uuid.UUID):
    from . import models
    from app.assessment_delivery.models import AssessmentPublication
    link=await session.scalar(select(models.HQActivityDeliveryLink).where(
        models.HQActivityDeliveryLink.organization_id==actor.organization_id,
        models.HQActivityDeliveryLink.id==link_id).with_for_update())
    if link is None: raise HTTPException(404,"Aplicação não encontrada.")
    publication=await session.scalar(select(AssessmentPublication).where(
        AssessmentPublication.organization_id == actor.organization_id,
        AssessmentPublication.id == link.publication_id,
    ))
    if publication is None: raise HTTPException(404,"Publicação canônica não encontrada.")
    publication.status="PUBLISHED";publication.published_by_user_id=actor.user_id;publication.published_at=datetime.now(UTC)
    link.status="PUBLISHED";link.published_by_user_id=actor.user_id;link.published_at=datetime.now(UTC)
    await session.flush();return link,publication

async def monitoring_summary(session:AsyncSession,*,actor:ActorContext,link_id:uuid.UUID)->dict[str,Any]:
    from . import models
    from app.assessment_delivery.models import AssessmentSession, AssessmentSessionEvent
    link=await session.scalar(select(models.HQActivityDeliveryLink).where(
        models.HQActivityDeliveryLink.organization_id==actor.organization_id,
        models.HQActivityDeliveryLink.id==link_id))
    if link is None: raise HTTPException(404,"Aplicação não encontrada.")
    sessions=list((await session.scalars(select(AssessmentSession).where(
        AssessmentSession.organization_id==actor.organization_id,
        AssessmentSession.publication_id==link.publication_id))).all())
    counts={}
    for item in sessions: counts[item.status]=counts.get(item.status,0)+1
    return {
        "delivery_id":str(link.id),
        "publication_id":str(link.publication_id),
        "status":link.status,
        "total_sessions":len(sessions),
        "by_status":counts,
        "started":sum(v for k,v in counts.items() if k not in {"CREATED"}),
        "completed":sum(v for k,v in counts.items() if k in {"SUBMITTED","COMPLETED"}),
        "in_progress":sum(v for k,v in counts.items() if k in {"STARTED","IN_PROGRESS","PAUSED"}),
        "monitoring_settings":link.monitoring_settings,
    }
