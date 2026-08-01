from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services.infrastructure import (
    calculate_capacity_recommendation,
    dr_readiness,
    render_argocd_application,
    render_hpa_values,
)
from app.services.object_storage import LocalObjectStorage, ObjectStorageError, normalize_object_key


def test_sprint_13_3_revision_fits_alembic_column():
    assert len("0027_infra_continuity") <= 32


def test_object_key_normalization_blocks_traversal():
    assert normalize_object_key("org//projects\\file.pdf") == "org/projects/file.pdf"
    with pytest.raises(ObjectStorageError):
        normalize_object_key("../../secrets.env")


@pytest.mark.asyncio
async def test_local_object_storage_roundtrip(tmp_path):
    storage = LocalObjectStorage(tmp_path)
    metadata = await storage.put_bytes("org/report.txt", b"educode", "text/plain")
    assert metadata.size_bytes == 7
    assert len(metadata.checksum_sha256) == 64
    assert await storage.get_bytes("org/report.txt") == b"educode"
    health = await storage.healthcheck()
    assert health["status"] == "healthy"
    await storage.delete("org/report.txt")


def test_capacity_recommendation_respects_limits():
    policy = SimpleNamespace(
        enabled=True,
        component="worker-ai",
        min_replicas=2,
        max_replicas=8,
        target_cpu_percent=70,
        target_memory_percent=75,
        queue_depth_target=10,
    )
    result = calculate_capacity_recommendation(
        policy,
        current_replicas=2,
        cpu_percent=95,
        memory_percent=80,
        queue_depth=70,
    )
    assert result["recommended_replicas"] == 7
    assert result["recommended_replicas"] <= policy.max_replicas


def test_dr_readiness_requires_recovery_and_replication():
    plan = SimpleNamespace(id=uuid4(), rpo_minutes=60, runbook_json={}, last_exercised_at=None)
    primary = SimpleNamespace(status="healthy")
    recovery = SimpleNamespace(status="unavailable")
    result = dr_readiness(plan, primary=primary, recovery=recovery, replication=None)
    assert result["ready"] is False
    assert any("recuperação" in item for item in result["blockers"])
    assert any("replicação" in item for item in result["blockers"])


def test_dr_readiness_accepts_healthy_topology():
    plan = SimpleNamespace(id=uuid4(), rpo_minutes=60, runbook_json={"steps": ["validate"]}, last_exercised_at="2026-07-24")
    primary = SimpleNamespace(status="healthy")
    recovery = SimpleNamespace(status="healthy")
    replication = SimpleNamespace(status="healthy", lag_seconds=10)
    result = dr_readiness(plan, primary=primary, recovery=recovery, replication=replication)
    assert result["ready"] is True
    assert result["score"] == 100.0


def test_argocd_manifest_and_hpa_values_are_reproducible():
    app = SimpleNamespace(
        name="educode-homolog",
        repository_url="https://github.com/example/infra.git",
        target_revision="main",
        manifest_path="infra/gitops/overlays/homologation",
        namespace="educode-homolog",
        sync_policy="automated_prune",
    )
    cluster = SimpleNamespace(api_endpoint="https://kubernetes.default.svc")
    manifest = render_argocd_application(app, cluster)
    assert "kind: Application" in manifest
    assert "prune: true" in manifest
    policy = SimpleNamespace(
        enabled=True,
        min_replicas=2,
        max_replicas=10,
        target_cpu_percent=70,
        target_memory_percent=75,
        queue_depth_target=20,
        scale_down_stabilization_seconds=300,
    )
    values = render_hpa_values(policy)
    assert values["maxReplicas"] == 10
    assert values["queueDepthTarget"] == 20


def test_sprint_13_3_settings_are_safe_by_default():
    settings = Settings()
    assert tuple(map(int, settings.app_version.split("."))) >= (0, 14, 0)
    assert settings.object_storage_provider == "local"
    assert settings.kubernetes_enabled is False
    assert settings.gitops_enabled is False
    assert settings.dr_automatic_failover_enabled is False
