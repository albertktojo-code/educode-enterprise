from __future__ import annotations

import math
from typing import Any

from app.models.infrastructure import (
    AutoscalingPolicy,
    DisasterRecoveryPlan,
    GitOpsApplication,
    InfrastructureCluster,
    StorageReplicationLink,
)


def cluster_is_healthy(cluster: InfrastructureCluster) -> bool:
    return cluster.status == "healthy"


def calculate_capacity_recommendation(
    policy: AutoscalingPolicy,
    *,
    current_replicas: int,
    cpu_percent: float,
    memory_percent: float,
    queue_depth: int,
) -> dict[str, Any]:
    current = max(0, current_replicas)
    if not policy.enabled:
        return {
            "component": policy.component,
            "current_replicas": current,
            "recommended_replicas": current,
            "reason": "Escalonamento automático desativado",
            "signals": {"cpu": cpu_percent, "memory": memory_percent, "queue_depth": float(queue_depth)},
        }
    baseline = max(current, policy.min_replicas, 1)
    cpu_need = math.ceil(baseline * cpu_percent / max(policy.target_cpu_percent, 1))
    memory_need = math.ceil(baseline * memory_percent / max(policy.target_memory_percent, 1))
    queue_need = math.ceil(queue_depth / max(policy.queue_depth_target, 1)) if queue_depth else policy.min_replicas
    recommended = max(policy.min_replicas, cpu_need, memory_need, queue_need)
    recommended = min(policy.max_replicas, recommended)
    if recommended > current:
        reason = "Escalar horizontalmente por pressão de CPU, memória ou fila"
    elif recommended < current:
        reason = "Há capacidade ociosa; respeitar janela de estabilização antes de reduzir"
    else:
        reason = "Capacidade atual compatível com os sinais observados"
    return {
        "component": policy.component,
        "current_replicas": current,
        "recommended_replicas": recommended,
        "reason": reason,
        "signals": {
            "cpu": round(cpu_percent, 2),
            "memory": round(memory_percent, 2),
            "queue_depth": float(queue_depth),
        },
    }


def dr_readiness(
    plan: DisasterRecoveryPlan,
    *,
    primary: InfrastructureCluster,
    recovery: InfrastructureCluster,
    replication: StorageReplicationLink | None,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if primary.status != "healthy":
        warnings.append("Cluster primário não está saudável")
    if recovery.status != "healthy":
        blockers.append("Cluster de recuperação não está saudável")
    if replication is None:
        blockers.append("Plano sem replicação de armazenamento configurada")
        replication_status = "missing"
    else:
        replication_status = replication.status
        if replication.status not in {"healthy", "active", "configured"}:
            blockers.append("Replicação de armazenamento indisponível")
        if replication.lag_seconds > plan.rpo_minutes * 60:
            blockers.append("Atraso da replicação excede o RPO definido")
    if not plan.runbook_json:
        warnings.append("Runbook de recuperação ainda não foi preenchido")
    if plan.last_exercised_at is None:
        warnings.append("Plano ainda não foi exercitado")
    score = 100.0 - min(80.0, len(blockers) * 30.0) - min(20.0, len(warnings) * 5.0)
    return {
        "plan_id": plan.id,
        "ready": not blockers,
        "score": max(0.0, score),
        "blockers": blockers,
        "warnings": warnings,
        "primary_status": primary.status,
        "recovery_status": recovery.status,
        "replication_status": replication_status,
    }


def render_argocd_application(application: GitOpsApplication, cluster: InfrastructureCluster) -> str:
    automated = application.sync_policy.startswith("automated")
    prune = application.sync_policy == "automated_prune"
    sync_policy = "  syncPolicy:\n    automated:\n      selfHeal: true\n      prune: %s\n" % str(prune).lower() if automated else ""
    return (
        "apiVersion: argoproj.io/v1alpha1\n"
        "kind: Application\n"
        "metadata:\n"
        f"  name: {application.name}\n"
        "  namespace: argocd\n"
        "spec:\n"
        "  project: default\n"
        "  source:\n"
        f"    repoURL: {application.repository_url}\n"
        f"    targetRevision: {application.target_revision}\n"
        f"    path: {application.manifest_path}\n"
        "  destination:\n"
        f"    server: {cluster.api_endpoint or 'https://kubernetes.default.svc'}\n"
        f"    namespace: {application.namespace}\n"
        f"{sync_policy}"
    )


def render_hpa_values(policy: AutoscalingPolicy) -> dict[str, Any]:
    return {
        "enabled": policy.enabled,
        "minReplicas": policy.min_replicas,
        "maxReplicas": policy.max_replicas,
        "targetCPUUtilizationPercentage": policy.target_cpu_percent,
        "targetMemoryUtilizationPercentage": policy.target_memory_percent,
        "queueDepthTarget": policy.queue_depth_target,
        "scaleDownStabilizationSeconds": policy.scale_down_stabilization_seconds,
    }
