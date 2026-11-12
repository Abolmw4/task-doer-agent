import os

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from openinference.instrumentation.langchain import LangChainInstrumentor


def setup_phoenix():

    # Phoenix OTLP HTTP endpoint
    endpoint = os.getenv(
        "PHOENIX_COLLECTOR_ENDPOINT",
        "http://127.0.0.1:6006/v1/traces"
    )

    # Create OpenTelemetry provider
    tracer_provider = TracerProvider()

    # Configure exporter
    exporter = OTLPSpanExporter(
        endpoint=endpoint
    )

    # Batch processing
    tracer_provider.add_span_processor(
        BatchSpanProcessor(exporter)
    )

    # Register global tracer provider
    trace_api.set_tracer_provider(tracer_provider)

    # Instrument LangChain and LangGraph
    LangChainInstrumentor().instrument(
        tracer_provider=tracer_provider
    )

    print("Phoenix monitoring initialized!")

    return tracer_provider