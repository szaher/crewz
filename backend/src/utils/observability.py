"""
OpenTelemetry Configuration for Distributed Tracing and Metrics

This module sets up OpenTelemetry instrumentation for the CrewAI platform,
including automatic instrumentation for FastAPI, SQLAlchemy, Redis, and HTTP clients.
"""

import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

logger = logging.getLogger(__name__)


class ObservabilityConfig:
    """OpenTelemetry configuration and setup."""

    def __init__(
        self,
        service_name: str = "crewai-backend",
        service_version: str = "1.0.0",
        otlp_endpoint: Optional[str] = None,
        enable_tracing: bool = True,
        enable_metrics: bool = True,
        enable_logging: bool = True,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint or "http://otel-collector:4317"
        self.enable_tracing = enable_tracing
        self.enable_metrics = enable_metrics
        self.enable_logging = enable_logging

        self.tracer: Optional[trace.Tracer] = None
        self.meter: Optional[metrics.Meter] = None

    def setup(self) -> None:
        """Initialize OpenTelemetry instrumentation."""
        # Create resource with service information
        resource = Resource.create(
            {
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
                "deployment.environment": "production",  # Override via env var
            }
        )

        if self.enable_tracing:
            self._setup_tracing(resource)

        if self.enable_metrics:
            self._setup_metrics(resource)

        if self.enable_logging:
            self._setup_logging()

        logger.info(
            f"OpenTelemetry initialized for {self.service_name} v{self.service_version}"
        )

    def _setup_tracing(self, resource: Resource) -> None:
        """Configure distributed tracing."""
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Create OTLP span exporter
        otlp_span_exporter = OTLPSpanExporter(
            endpoint=self.otlp_endpoint,
            insecure=True,  # Use TLS in production
        )

        # Add span processor with batch export
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                otlp_span_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,
            )
        )

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Get tracer instance
        self.tracer = trace.get_tracer(__name__)

        logger.info(f"Tracing configured with OTLP endpoint: {self.otlp_endpoint}")

    def _setup_metrics(self, resource: Resource) -> None:
        """Configure metrics collection."""
        # Create OTLP metric exporter
        otlp_metric_exporter = OTLPMetricExporter(
            endpoint=self.otlp_endpoint,
            insecure=True,  # Use TLS in production
        )

        # Create metric reader with periodic export
        metric_reader = PeriodicExportingMetricReader(
            otlp_metric_exporter,
            export_interval_millis=60000,  # Export every 60 seconds
        )

        # Create meter provider
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )

        # Set global meter provider
        metrics.set_meter_provider(meter_provider)

        # Get meter instance
        self.meter = metrics.get_meter(__name__)

        logger.info("Metrics configured with OTLP endpoint")

    def _setup_logging(self) -> None:
        """Configure logging instrumentation."""
        LoggingInstrumentor().instrument(set_logging_format=True)
        logger.info("Logging instrumentation enabled")

    def instrument_app(self, app) -> None:
        """Instrument FastAPI application with automatic tracing."""
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")

    def instrument_sqlalchemy(self, engine) -> None:
        """Instrument SQLAlchemy engine with automatic tracing."""
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,
            commenter_options={},
        )
        logger.info("SQLAlchemy instrumentation enabled")

    def instrument_redis(self) -> None:
        """Instrument Redis client with automatic tracing."""
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")

    def instrument_http_clients(self) -> None:
        """Instrument HTTP requests library with automatic tracing."""
        RequestsInstrumentor().instrument()
        logger.info("HTTP client instrumentation enabled")


# Global observability instance
_observability: Optional[ObservabilityConfig] = None


def get_observability() -> ObservabilityConfig:
    """Get global observability configuration."""
    global _observability
    if _observability is None:
        raise RuntimeError("Observability not initialized. Call setup_observability() first.")
    return _observability


def setup_observability(
    service_name: str = "crewai-backend",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
) -> ObservabilityConfig:
    """Initialize and configure OpenTelemetry observability."""
    global _observability

    if _observability is not None:
        logger.warning("Observability already initialized")
        return _observability

    _observability = ObservabilityConfig(
        service_name=service_name,
        service_version=service_version,
        otlp_endpoint=otlp_endpoint,
    )

    _observability.setup()

    # Instrument common libraries
    _observability.instrument_redis()
    _observability.instrument_http_clients()

    return _observability


# Custom metrics helpers
def create_counter(name: str, description: str = "", unit: str = "1"):
    """Create a counter metric."""
    obs = get_observability()
    return obs.meter.create_counter(name=name, description=description, unit=unit)


def create_histogram(name: str, description: str = "", unit: str = "1"):
    """Create a histogram metric."""
    obs = get_observability()
    return obs.meter.create_histogram(name=name, description=description, unit=unit)


def create_up_down_counter(name: str, description: str = "", unit: str = "1"):
    """Create an up/down counter metric."""
    obs = get_observability()
    return obs.meter.create_up_down_counter(name=name, description=description, unit=unit)


# Application-specific metrics
class AppMetrics:
    """Application-specific metrics definitions."""

    def __init__(self):
        # Request metrics
        self.http_requests_total = create_counter(
            "http_requests_total",
            description="Total HTTP requests",
            unit="1",
        )

        self.http_request_duration = create_histogram(
            "http_request_duration_seconds",
            description="HTTP request duration",
            unit="s",
        )

        # Flow execution metrics
        self.flow_executions_total = create_counter(
            "flow_executions_total",
            description="Total flow executions",
            unit="1",
        )

        self.flow_execution_duration = create_histogram(
            "flow_execution_duration_seconds",
            description="Flow execution duration",
            unit="s",
        )

        self.flow_executions_active = create_up_down_counter(
            "flow_executions_active",
            description="Currently active flow executions",
            unit="1",
        )

        # LLM metrics
        self.llm_requests_total = create_counter(
            "llm_requests_total",
            description="Total LLM API requests",
            unit="1",
        )

        self.llm_tokens_total = create_counter(
            "llm_tokens_total",
            description="Total LLM tokens consumed",
            unit="1",
        )

        self.llm_cost_total = create_counter(
            "llm_cost_total",
            description="Total LLM cost",
            unit="USD",
        )

        # Tool execution metrics
        self.tool_executions_total = create_counter(
            "tool_executions_total",
            description="Total tool executions",
            unit="1",
        )

        self.tool_execution_duration = create_histogram(
            "tool_execution_duration_seconds",
            description="Tool execution duration",
            unit="s",
        )

        # Database metrics
        self.db_queries_total = create_counter(
            "db_queries_total",
            description="Total database queries",
            unit="1",
        )

        self.db_query_duration = create_histogram(
            "db_query_duration_seconds",
            description="Database query duration",
            unit="s",
        )

        # Cache metrics
        self.cache_hits_total = create_counter(
            "cache_hits_total",
            description="Total cache hits",
            unit="1",
        )

        self.cache_misses_total = create_counter(
            "cache_misses_total",
            description="Total cache misses",
            unit="1",
        )

    def record_http_request(self, method: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        self.http_requests_total.add(1, {"method": method, "status": str(status_code)})
        self.http_request_duration.record(duration, {"method": method, "status": str(status_code)})

    def record_flow_execution(self, status: str, duration: float):
        """Record flow execution metrics."""
        self.flow_executions_total.add(1, {"status": status})
        self.flow_execution_duration.record(duration, {"status": status})

    def record_llm_request(self, provider: str, model: str, tokens: int, cost: float):
        """Record LLM request metrics."""
        labels = {"provider": provider, "model": model}
        self.llm_requests_total.add(1, labels)
        self.llm_tokens_total.add(tokens, labels)
        self.llm_cost_total.add(cost, labels)


# Global metrics instance
app_metrics: Optional[AppMetrics] = None


def get_app_metrics() -> AppMetrics:
    """Get application metrics instance."""
    global app_metrics
    if app_metrics is None:
        app_metrics = AppMetrics()
    return app_metrics
