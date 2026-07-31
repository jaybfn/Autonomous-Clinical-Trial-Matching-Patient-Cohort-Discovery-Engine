"""Build production AgentBundle + graph runner from settings (ADC / WI)."""

from __future__ import annotations

from trialmatch.adapters.llm_client import build_llm_client
from trialmatch.adapters.qdrant_client import QdrantVectorStore
from trialmatch.adapters.snowflake_client import agent_read_client, audit_write_client
from trialmatch.agents.auditor.agent import AuditorAgent
from trialmatch.agents.auditor.sink import AuditSink
from trialmatch.agents.compliance.agent import ComplianceAgent
from trialmatch.agents.matcher.agent import MatcherAgent
from trialmatch.agents.parser.agent import ParserAgent
from trialmatch.config.settings import Settings
from trialmatch.orchestrator.graph import AgentBundle, CompiledGraphRunner, build_match_graph
from trialmatch.services.embeddings import build_embedder


def build_default_graph_runner(settings: Settings) -> CompiledGraphRunner:
    """Wire live adapters. Unit tests should override `get_graph_runner` instead."""
    compliance = ComplianceAgent()
    parser = ParserAgent(llm=build_llm_client(settings))
    matcher = MatcherAgent(
        snowflake=agent_read_client(settings),
        qdrant=QdrantVectorStore(settings=settings),
        embedder=build_embedder(settings),
        schema=settings.matcher_snowflake_schema,
        vector_limit=settings.matcher_vector_limit,
    )
    auditor = AuditorAgent(
        sink=AuditSink(
            client=audit_write_client(settings),
            schema=settings.auditor_snowflake_schema,
        )
    )
    graph = build_match_graph(
        AgentBundle(
            compliance=compliance,
            parser=parser,
            matcher=matcher,
            auditor=auditor,
        )
    )
    return CompiledGraphRunner(graph)
