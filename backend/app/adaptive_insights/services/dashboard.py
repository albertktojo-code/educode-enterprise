from __future__ import annotations

from ..schemas import InstitutionalPathDashboardInput, InstitutionalPathDashboardResult


def build_institutional_path_dashboard(
    payload: InstitutionalPathDashboardInput,
) -> InstitutionalPathDashboardResult:
    paths = payload.paths
    assigned = sum(item.assigned_students for item in paths)
    active = sum(item.active_students for item in paths)
    completed = sum(item.completed_students for item in paths)
    weights = [max(item.assigned_students, 1) for item in paths]
    total_weight = sum(weights)
    average_progress = (
        sum(item.average_progress * weight for item, weight in zip(paths, weights, strict=True)) / total_weight
        if total_weight
        else 0
    )
    average_mastery = (
        sum(item.average_mastery * weight for item, weight in zip(paths, weights, strict=True)) / total_weight
        if total_weight
        else 0
    )
    attention = [
        item.path_id
        for item in paths
        if item.average_progress < 0.45
        or item.average_mastery < 0.45
        or item.overdue_reviews > max(3, item.active_students // 4)
    ]
    return InstitutionalPathDashboardResult(
        paths_count=len(paths),
        assigned_students=assigned,
        active_students=active,
        completed_students=completed,
        completion_rate=round(completed / assigned, 4) if assigned else 0,
        average_progress=round(average_progress, 4),
        average_mastery=round(average_mastery, 4),
        overdue_reviews=sum(item.overdue_reviews for item in paths),
        interventions_count=sum(item.interventions_count for item in paths),
        attention_paths=attention,
    )
