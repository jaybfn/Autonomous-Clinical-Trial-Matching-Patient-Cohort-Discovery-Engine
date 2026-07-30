"""Parser agent — scrubbed note → LLM JSON → validated clinical features."""

from __future__ import annotations

import json
from dataclasses import dataclass

from trialmatch.adapters.llm_client import LlmClient
from trialmatch.agents.parser.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from trialmatch.agents.parser.schemas import ParsedClinicalFeatures
from trialmatch.observability.logging import get_logger, sanitize_log_extra

logger = get_logger(__name__)

AGENT_NAME = "parser"
AGENT_VERSION = "0.1.0"


class ParserError(RuntimeError):
    """Fail-closed error when parsing / validation cannot complete safely."""


@dataclass(frozen=True, slots=True)
class ParseResult:
    features: ParsedClinicalFeatures
    prompt_version: str
    agent_version: str = AGENT_VERSION


class ParserAgent:
    """Calls an injected LLM client and validates output against Pydantic schemas."""

    def __init__(self, *, llm: LlmClient) -> None:
        self._llm = llm

    def parse(
        self,
        *,
        scrubbed_text: str,
        patient_id: str,
        correlation_id: str | None = None,
    ) -> ParseResult:
        if not scrubbed_text or not scrubbed_text.strip():
            raise ParserError("scrubbed_text must not be blank")
        if not patient_id or not patient_id.strip():
            raise ParserError("patient_id must not be blank")

        user = build_user_prompt(scrubbed_text)
        try:
            raw = self._llm.complete_json(system=SYSTEM_PROMPT, user=user)
        except Exception as exc:  # noqa: BLE001 — fail closed
            raise ParserError(f"LLM completion failed: {exc}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParserError(f"LLM returned invalid JSON: {exc}") from exc

        if not isinstance(payload, dict):
            raise ParserError("LLM JSON must be an object")

        # patient_id comes from the orchestrator / event — never trust the model for it.
        payload = {**payload, "patient_id": patient_id.strip()}
        try:
            features = ParsedClinicalFeatures.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"Feature schema validation failed: {exc}") from exc

        result = ParseResult(features=features, prompt_version=PROMPT_VERSION)
        logger.info(
            "parser.parse.completed",
            extra=sanitize_log_extra(
                {
                    "agent_name": AGENT_NAME,
                    "correlation_id": correlation_id or "",
                    "prompt_version": PROMPT_VERSION,
                    "condition_count": len(features.conditions),
                    "lab_count": len(features.labs),
                    "status": "ok",
                }
            ),
        )
        return result
