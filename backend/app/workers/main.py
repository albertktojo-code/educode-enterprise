from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.anime_studio.rendering import render_anime_job
from app.core.config import get_settings
from app.db.session import AsyncSessionFactory
from app.models.ai_runtime import AIGenerationRequest
from app.models.operations import (
    BackgroundJob,
    BackgroundJobAttempt,
    ProviderCircuitState,
    ResourceReservation,
    WorkerHeartbeat,
)
from app.models.platform import BackupRun, RestoreTest
from app.services.ai.orchestrator import run_generation
from app.services.operations import (
    add_job_event,
    create_job_notification,
    dependencies_satisfied,
    get_redis,
    is_transient_error,
    push_job,
    redis_key,
    retry_delay_seconds,
    utcnow,
)
from app.services.platform import execute_backup, execute_restore_test

settings = get_settings()
ProgressCallback = Callable[[int, str, dict[str, Any] | None], Awaitable[None]]


class JobCancelledError(RuntimeError):
    pass


async def update_heartbeat(
    worker_name: str,
    queue_name: str,
    *,
    status: str | None = None,
    current_job_id: UUID | None = None,
    preserve_current_job: bool = False,
) -> None:
    async with AsyncSessionFactory() as session:
        heartbeat = await session.scalar(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == worker_name)
        )
        if heartbeat is None:
            heartbeat = WorkerHeartbeat(
                worker_name=worker_name,
                queue_name=queue_name,
                hostname=socket.gethostname(),
                process_id=os.getpid(),
            )
            session.add(heartbeat)
        if status is not None:
            heartbeat.status = status
        if not preserve_current_job:
            heartbeat.current_job_id = current_job_id
        heartbeat.last_seen_at = utcnow()
        await session.commit()


async def heartbeat_loop(worker_name: str, queue_name: str) -> None:
    while True:
        try:
            await update_heartbeat(worker_name, queue_name, preserve_current_job=True)
        except Exception:
            pass
        await asyncio.sleep(settings.worker_heartbeat_seconds)


async def generic_steps_handler(job: BackgroundJob, progress: ProgressCallback) -> dict[str, Any]:
    steps_by_type = {
        "document_processing": [
            "Validando arquivo",
            "Extraindo conteúdo",
            "Criando chunks",
            "Gerando embeddings",
            "Atualizando índice",
        ],
        "document_indexing": ["Preparando chunks", "Gerando embeddings", "Atualizando índice"],
        "analytics_refresh": [
            "Selecionando tentativas válidas",
            "Calculando evidências",
            "Atualizando métricas",
            "Gerando alertas",
        ],
        "assessment_recalculation": [
            "Validando gabaritos",
            "Recalculando respostas",
            "Atualizando tentativas",
            "Publicando evidências",
        ],
        "statistical_report": [
            "Congelando dataset",
            "Executando cálculos",
            "Gerando gráficos",
            "Montando relatório",
        ],
        "assessment_import": [
            "Validando arquivo",
            "Mapeando campos",
            "Importando questões",
            "Preparando revisão",
        ],
        "media_generation": [
            "Preparando referências",
            "Gerando mídia",
            "Validando resultado",
            "Salvando artefato",
        ],
    }
    custom_steps = job.input_snapshot.get("steps") if isinstance(job.input_snapshot, dict) else None
    steps = (
        [str(item) for item in custom_steps if str(item).strip()]
        if isinstance(custom_steps, list) and custom_steps
        else steps_by_type.get(
            job.job_type, ["Preparando", "Executando", "Validando", "Finalizando"]
        )
    )
    total = len(steps)
    for index, step in enumerate(steps, start=1):
        await progress(int(index / total * 95), step, {"step": index, "total": total})
        await asyncio.sleep(settings.worker_step_delay_ms / 1000)
    return {"job_type": job.job_type, "processed": True, "steps": steps}


async def update_provider_circuit(
    session, *, organization_id: UUID, provider_id: UUID | None, success: bool, error: str = ""
) -> None:
    if provider_id is None:
        return
    circuit = await session.scalar(
        select(ProviderCircuitState).where(
            ProviderCircuitState.organization_id == organization_id,
            ProviderCircuitState.provider_id == provider_id,
        )
    )
    if circuit is None:
        circuit = ProviderCircuitState(organization_id=organization_id, provider_id=provider_id)
        session.add(circuit)
    if success:
        circuit.state = "closed"
        circuit.consecutive_failures = 0
        circuit.opened_at = None
        circuit.next_probe_at = None
        circuit.last_error = ""
    else:
        circuit.consecutive_failures += 1
        circuit.last_error = error[:4000]
        if circuit.consecutive_failures >= circuit.failure_threshold:
            circuit.state = "open"
            circuit.opened_at = utcnow()
            circuit.next_probe_at = utcnow() + timedelta(minutes=5)


async def ensure_circuit_allows(session, request: AIGenerationRequest) -> None:
    if request.provider_id is None:
        return
    circuit = await session.scalar(
        select(ProviderCircuitState).where(
            ProviderCircuitState.organization_id == request.organization_id,
            ProviderCircuitState.provider_id == request.provider_id,
        )
    )
    if circuit and circuit.state == "open":
        if circuit.next_probe_at and circuit.next_probe_at > utcnow():
            raise RuntimeError("Provedor temporariamente indisponível: circuit breaker aberto")
        circuit.state = "half_open"


async def process_job(job_id: UUID, worker_name: str) -> None:
    async with AsyncSessionFactory() as session:
        job = await session.scalar(
            select(BackgroundJob).where(BackgroundJob.id == job_id).with_for_update()
        )
        if job is None or job.status == "completed":
            return
        if job.status in {"processing", "waiting_provider", "validating"}:
            return
        if job.cancel_requested or job.status == "cancelled":
            job.status = "cancelled"
            job.completed_at = utcnow()
            await session.commit()
            return
        if not await dependencies_satisfied(session, job.id):
            job.status = "queued"
            job.current_step = "Aguardando dependências"
            await session.commit()
            await asyncio.sleep(2)
            await push_job(job)
            return
        job.status = "processing"
        job.started_at = job.started_at or utcnow()
        job.current_step = "Iniciando"
        attempt_number = job.retry_count + 1
        attempt = BackgroundJobAttempt(
            organization_id=job.organization_id,
            job_id=job.id,
            attempt_number=attempt_number,
            worker_name=worker_name,
            status="processing",
        )
        session.add(attempt)
        await add_job_event(
            session,
            job=job,
            event_type="job.started",
            event_data={"worker": worker_name, "attempt": attempt_number},
        )
        await session.commit()

    async def progress(percent: int, step: str, data: dict[str, Any] | None = None) -> None:
        async with AsyncSessionFactory() as progress_session:
            current = await progress_session.get(BackgroundJob, job_id)
            if current is None:
                raise JobCancelledError("Tarefa não encontrada")
            if current.cancel_requested:
                raise JobCancelledError("Cancelamento solicitado")
            current.progress_percent = max(0, min(percent, 100))
            current.current_step = step
            await add_job_event(
                progress_session,
                job=current,
                event_type="job.progress",
                event_data={"progress": current.progress_percent, "step": step, **(data or {})},
            )
            await progress_session.commit()

    try:
        await update_heartbeat(worker_name, job.queue_name, status="busy", current_job_id=job.id)
        if job.job_type == "anime_render":
            result = await render_anime_job(job, progress)
        elif job.job_type == "platform_restore_test":
            await progress(10, "Validando checksum e arquivo")
            async with AsyncSessionFactory() as restore_session:
                restore_test = await restore_session.get(
                    RestoreTest,
                    UUID(str(job.input_snapshot["restore_test_id"])),
                )
                backup = await restore_session.get(
                    BackupRun,
                    UUID(str(job.input_snapshot["backup_run_id"])),
                )
                if restore_test is None or backup is None:
                    raise RuntimeError("Registro do teste de restauração não encontrado")
                restore_test.status = "running"
                restore_test.started_at = utcnow()
                await restore_session.commit()
            await progress(30, "Criando banco temporário isolado")
            try:
                restore_result = await asyncio.to_thread(execute_restore_test, backup)
                async with AsyncSessionFactory() as restore_session:
                    stored_test = await restore_session.get(RestoreTest, restore_test.id)
                    if stored_test is None:
                        raise RuntimeError("Teste de restauração desapareceu")
                    stored_test.status = "passed"
                    stored_test.validation_summary = restore_result
                    stored_test.completed_at = utcnow()
                    await restore_session.commit()
                result = {
                    "backup_run_id": str(backup.id),
                    "restore_test_id": str(restore_test.id),
                    **restore_result,
                }
                await progress(95, "Restauração temporária concluída")
            except Exception as exc:
                async with AsyncSessionFactory() as restore_session:
                    stored_test = await restore_session.get(RestoreTest, restore_test.id)
                    if stored_test is not None:
                        stored_test.status = "failed"
                        stored_test.error_message = str(exc)[:4000]
                        stored_test.completed_at = utcnow()
                        await restore_session.commit()
                raise
        elif job.job_type == "platform_backup":
            await progress(10, "Preparando backup seguro")
            async with AsyncSessionFactory() as backup_session:
                backup = await backup_session.get(
                    BackupRun, UUID(str(job.input_snapshot["backup_run_id"]))
                )
                if backup is None:
                    raise RuntimeError("Registro de backup não encontrado")
                backup.status = "processing"
                backup.started_at = utcnow()
                await backup_session.commit()
            await progress(30, "Exportando banco e arquivos")
            try:
                backup_result = await asyncio.to_thread(execute_backup, backup)
                async with AsyncSessionFactory() as backup_session:
                    stored = await backup_session.get(BackupRun, backup.id)
                    if stored is None:
                        raise RuntimeError("Registro de backup desapareceu")
                    stored.status = "completed"
                    stored.storage_path = str(backup_result["storage_path"])
                    stored.checksum_sha256 = str(backup_result["checksum_sha256"])
                    stored.size_bytes = int(backup_result["size_bytes"])
                    stored.manifest = dict(backup_result["manifest"])
                    stored.completed_at = utcnow()
                    await backup_session.commit()
                result = {"backup_run_id": str(backup.id), **backup_result}
                await progress(95, "Backup validado e armazenado")
            except Exception as exc:
                async with AsyncSessionFactory() as backup_session:
                    stored = await backup_session.get(BackupRun, backup.id)
                    if stored is not None:
                        stored.status = "failed"
                        stored.error_code = "BACKUP_FAILED"
                        stored.error_message = str(exc)[:4000]
                        stored.completed_at = utcnow()
                        await backup_session.commit()
                raise
        elif job.job_type == "ai_generation":
            await progress(10, "Preparando contexto de IA")
            async with AsyncSessionFactory() as ai_session:
                queued_request = await ai_session.get(
                    AIGenerationRequest, UUID(str(job.input_snapshot["request_id"]))
                )
                if queued_request is None:
                    raise RuntimeError("Solicitação de IA não encontrada")
                await ensure_circuit_allows(ai_session, queued_request)
                ai_request = await run_generation(
                    ai_session,
                    organization_id=job.organization_id,
                    request_id=UUID(str(job.input_snapshot["request_id"])),
                )
                if ai_request.status == "failed":
                    await update_provider_circuit(
                        ai_session,
                        organization_id=ai_request.organization_id,
                        provider_id=ai_request.provider_id,
                        success=False,
                        error=ai_request.error_message,
                    )
                    await ai_session.commit()
                    raise RuntimeError(ai_request.error_message or "Falha na geração de IA")
                await update_provider_circuit(
                    ai_session,
                    organization_id=ai_request.organization_id,
                    provider_id=ai_request.provider_id,
                    success=True,
                )
                await ai_session.commit()
            result = {"request_id": job.input_snapshot["request_id"], "ai_flow_id": job.ai_flow_id}
            await progress(95, "Resultado de IA validado")
        else:
            result = await generic_steps_handler(job, progress)
        async with AsyncSessionFactory() as complete_session:
            current = await complete_session.get(BackgroundJob, job_id)
            current.status = "completed"
            current.progress_percent = 100
            current.current_step = "Concluído"
            current.result_reference = result
            current.completed_at = utcnow()
            current.error_code = ""
            current.error_message = ""
            attempt = await complete_session.scalar(
                select(BackgroundJobAttempt).where(
                    BackgroundJobAttempt.job_id == job_id,
                    BackgroundJobAttempt.attempt_number == attempt_number,
                )
            )
            if attempt:
                attempt.status = "completed"
                attempt.completed_at = utcnow()
            reservation = await complete_session.scalar(
                select(ResourceReservation).where(
                    ResourceReservation.job_id == job_id,
                    ResourceReservation.status == "reserved",
                )
            )
            if reservation:
                reservation.status = "consumed"
                reservation.actual_cost = reservation.reserved_cost
                reservation.released_at = utcnow()
            await add_job_event(
                complete_session,
                job=current,
                event_type="job.completed",
                event_data={"result_reference": result},
            )
            await create_job_notification(
                complete_session,
                job=current,
                notification_type="job_completed",
                title="Tarefa concluída",
                message=f"{current.current_step}: {current.job_type}",
            )
            await complete_session.commit()
    except JobCancelledError as exc:
        async with AsyncSessionFactory() as cancel_session:
            current = await cancel_session.get(BackgroundJob, job_id)
            current.status = "cancelled"
            current.current_step = "Cancelado"
            current.completed_at = utcnow()
            await add_job_event(
                cancel_session,
                job=current,
                event_type="job.cancelled",
                event_data={"reason": str(exc)},
            )
            await create_job_notification(
                cancel_session,
                job=current,
                notification_type="job_cancelled",
                title="Tarefa cancelada",
                message=f"A tarefa {current.job_type} foi cancelada.",
            )
            await cancel_session.commit()
    except Exception as exc:
        async with AsyncSessionFactory() as error_session:
            current = await error_session.get(BackgroundJob, job_id)
            current.retry_count += 1
            transient = is_transient_error(exc)
            can_retry = transient and current.retry_count <= current.max_retries
            current.error_code = type(exc).__name__.upper()
            current.error_message = str(exc)[:4000]
            attempt = await error_session.scalar(
                select(BackgroundJobAttempt).where(
                    BackgroundJobAttempt.job_id == job_id,
                    BackgroundJobAttempt.attempt_number == attempt_number,
                )
            )
            if attempt:
                attempt.status = "failed"
                attempt.error_code = current.error_code
                attempt.error_message = current.error_message
                attempt.completed_at = utcnow()
            if can_retry:
                delay = retry_delay_seconds(current.retry_count)
                current.status = "retrying"
                current.current_step = f"Nova tentativa em {delay}s"
                current.run_after = utcnow() + timedelta(seconds=delay)
                await add_job_event(
                    error_session,
                    job=current,
                    event_type="job.retry_scheduled",
                    event_data={"delay_seconds": delay, "retry": current.retry_count},
                )
            else:
                current.status = "failed"
                current.current_step = "Falhou"
                current.completed_at = utcnow()
                await add_job_event(
                    error_session,
                    job=current,
                    event_type="job.failed",
                    event_data={"error_code": current.error_code, "transient": transient},
                )
                await create_job_notification(
                    error_session,
                    job=current,
                    notification_type="job_failed",
                    title="Falha em tarefa",
                    message=f"{current.job_type}: {current.error_message}",
                )
            await error_session.commit()
            if can_retry:

                async def requeue_later(job_id_to_queue: UUID, wait_seconds: int) -> None:
                    await asyncio.sleep(wait_seconds)
                    async with AsyncSessionFactory() as retry_session:
                        retry_job = await retry_session.get(BackgroundJob, job_id_to_queue)
                        if (
                            retry_job
                            and retry_job.status == "retrying"
                            and not retry_job.cancel_requested
                        ):
                            retry_job.status = "queued"
                            retry_job.current_step = "Na fila para nova tentativa"
                            await retry_session.commit()
                            await push_job(retry_job)

                asyncio.create_task(requeue_later(current.id, delay))
    finally:
        await update_heartbeat(worker_name, job.queue_name, status="idle", current_job_id=None)


async def recover_pending_jobs(queue_name: str) -> None:
    async with AsyncSessionFactory() as session:
        now = utcnow()
        stale_before = now - timedelta(minutes=10)
        jobs = list(
            (
                await session.scalars(
                    select(BackgroundJob)
                    .where(
                        BackgroundJob.queue_name == queue_name,
                        (
                            BackgroundJob.status.in_(["pending", "queued", "retrying"])
                            | (
                                BackgroundJob.status.in_(
                                    ["processing", "waiting_provider", "validating"]
                                )
                                & (BackgroundJob.updated_at < stale_before)
                            )
                        ),
                        (BackgroundJob.run_after.is_(None)) | (BackgroundJob.run_after <= now),
                        BackgroundJob.cancel_requested.is_(False),
                    )
                    .order_by(BackgroundJob.priority.desc(), BackgroundJob.created_at)
                    .limit(100)
                )
            ).all()
        )
        for job in jobs:
            if await push_job(job):
                job.status = "queued"
                job.queued_at = job.queued_at or now
                job.current_step = "Recuperada para a fila"
        await session.commit()


async def worker_is_draining(worker_name: str) -> bool:
    async with AsyncSessionFactory() as session:
        heartbeat = await session.scalar(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == worker_name)
        )
        return bool(heartbeat and heartbeat.status == "draining")


async def worker_loop(queue_name: str, worker_name: str) -> None:
    redis_client: Any = get_redis()
    heartbeat_task = asyncio.create_task(heartbeat_loop(worker_name, queue_name))
    try:
        while True:
            if await worker_is_draining(worker_name):
                await asyncio.sleep(2)
                continue
            keys = [
                redis_key(queue_name, "urgent"),
                redis_key(queue_name, "high"),
                redis_key(queue_name, "normal"),
                redis_key(queue_name, "low"),
            ]
            item = await redis_client.brpop(keys, timeout=5)
            if item is None:
                await recover_pending_jobs(queue_name)
                continue
            try:
                payload = json.loads(item[1])
                await process_job(UUID(payload["job_id"]), worker_name)
            except Exception as exc:
                print(f"worker_error queue={queue_name} error={exc}", flush=True)
    finally:
        heartbeat_task.cancel()
        await redis_client.aclose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EduCode background worker")
    parser.add_argument("--queue", default=os.getenv("WORKER_QUEUE", "default"))
    parser.add_argument("--name", default=os.getenv("WORKER_NAME"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    worker_name = args.name or f"{socket.gethostname()}-{args.queue}-{os.getpid()}"
    asyncio.run(worker_loop(args.queue, worker_name))


if __name__ == "__main__":
    main()
