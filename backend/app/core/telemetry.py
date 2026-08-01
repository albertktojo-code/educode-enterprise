from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.config import Settings, get_settings

logger = logging.getLogger("educode.telemetry")


def configure_telemetry(app: FastAPI, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        from app.db.session import engine

        provider = TracerProvider(
            resource=Resource.create({
                "service.name": settings.otel_service_name,
                "service.version": settings.app_version,
                "deployment.environment": settings.environment,
            }),
            sampler=ParentBased(TraceIdRatioBased(settings.trace_sample_ratio)),
        )
        if settings.otel_exporter_otlp_endpoint:
            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        HTTPXClientInstrumentor().instrument(tracer_provider=provider)
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=provider)
        logger.info("OpenTelemetry ativo para %s", settings.otel_service_name)
    except Exception as exc:  # observabilidade nunca pode impedir a aplicação de iniciar
        logger.warning("OpenTelemetry não foi inicializado: %s", exc)
