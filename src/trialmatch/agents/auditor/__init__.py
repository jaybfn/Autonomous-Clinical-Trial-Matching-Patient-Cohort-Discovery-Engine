"""Auditor agent package (justifications & append-only audit logs)."""

from trialmatch.agents.auditor.agent import AuditorAgent, AuditorError, AuditResult
from trialmatch.agents.auditor.report import build_justification_summary
from trialmatch.agents.auditor.sink import AuditSink, AuditSinkError

__all__ = [
    "AuditResult",
    "AuditSink",
    "AuditSinkError",
    "AuditorAgent",
    "AuditorError",
    "build_justification_summary",
]
