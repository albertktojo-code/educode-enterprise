from __future__ import annotations

from sqlalchemy import select

from . import models


async def get_model(session, organization_id, model_id):
    return await session.scalar(
        select(models.AssessmentAnalyticsModel).where(
            models.AssessmentAnalyticsModel.organization_id == organization_id,
            models.AssessmentAnalyticsModel.id == model_id,
        )
    )


async def get_report_definition(session, organization_id, report_id):
    return await session.scalar(
        select(models.AssessmentReportDefinition).where(
            models.AssessmentReportDefinition.organization_id == organization_id,
            models.AssessmentReportDefinition.id == report_id,
        )
    )
