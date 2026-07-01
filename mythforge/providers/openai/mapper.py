"""
Request/response mappers for OpenAI Responses API.

Maps between MythForge generic models (LLMRequest/LLMResponse) and
OpenAI-specific API format.  Zero provider-specific logic leaks into
the pipeline.

The Responses API uses a different format than the Chat Completions API:
- Input is a list of messages with role/content
- Output is a response object with output_text, usage, etc.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mythforge.providers.models import LLMRequest, LLMResponse, LLMStreamChunk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request Mapper
# ---------------------------------------------------------------------------

class OpenAIRequestMapper:
    """Maps :class:`LLMRequest` → OpenAI Responses API request dict.

    Uses the Responses API format (``input`` list, not ``messages``).
    """

    @staticmethod
    def to_responses_api(
        request: LLMRequest,
        model: str,
        *,
        max_output_tokens: int = 4096,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Build an OpenAI Responses API request dict.

        Parameters
        ----------
        request:
            MythForge generic LLM request.
        model:
            Resolved model name.
        max_output_tokens:
            Maximum output tokens.
        stream:
            Whether to enable streaming.

        Returns
        -------
        Dict[str, Any]
            OpenAI Responses API request body.
        """
        # Build input messages
        input_messages: List[Dict[str, Any]] = []

        if request.system_prompt:
            input_messages.append({
                "role": "developer",
                "content": request.system_prompt,
            })

        input_messages.append({
            "role": "user",
            "content": request.prompt,
        })

        body: Dict[str, Any] = {
            "model": model,
            "input": input_messages,
            "max_output_tokens": request.max_tokens if request.max_tokens else max_output_tokens,
            "stream": stream,
        }

        metadata = dict(request.metadata or {})
        response_format = metadata.get("response_format")
        if response_format is not None:
            body["response_format"] = response_format
        elif metadata.get("json_mode"):
            body["response_format"] = {"type": "json_object"}
        elif metadata.get("json_schema"):
            schema = metadata["json_schema"]
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": schema,
            }

        if metadata.get("reasoning_effort"):
            body["reasoning"] = {"effort": metadata["reasoning_effort"]}
        if metadata.get("modalities"):
            body["modalities"] = metadata["modalities"]
        if metadata.get("text_format"):
            body["text"] = {"format": metadata["text_format"]}

        # Temperature and top_p — only for non-reasoning models
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.top_p is not None and request.top_p < 1.0:
            body["top_p"] = request.top_p

        # Stop sequences (Responses API uses "stop")
        if request.stop_sequences:
            body["stop"] = request.stop_sequences

        # Store original metadata for response mapping
        body["_mythforge_metadata"] = {
            "original_metadata": request.metadata,
        }

        return body


# ---------------------------------------------------------------------------
# Response Mapper
# ---------------------------------------------------------------------------

class OpenAIResponseMapper:
    """Maps OpenAI Responses API response → :class:`LLMResponse`.

    Handles both synchronous and streaming response objects.
    """

    @staticmethod
    def from_responses_api(
        api_response: Any,
        provider: str = "openai",
        latency_ms: float = 0.0,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """Map an OpenAI Responses API response to :class:`LLMResponse`.

        Parameters
        ----------
        api_response:
            The OpenAI response object (from the SDK).
        provider:
            Provider name for attribution.
        latency_ms:
            Request latency in milliseconds.
        request_metadata:
            Original request metadata to propagate.

        Returns
        -------
        LLMResponse
            MythForge generic LLM response.
        """
        # Extract text — Responses API provides output_text
        text = ""
        if hasattr(api_response, "output_text"):
            text = api_response.output_text or ""
        elif hasattr(api_response, "text") and api_response.text:
            text = api_response.text or ""
        elif hasattr(api_response, "output") and api_response.output:
            # Parse structured output
            parts = []
            for item in api_response.output:
                if hasattr(item, "content") and item.content:
                    for block in item.content:
                        if hasattr(block, "text"):
                            parts.append(block.text)
            text = "".join(parts)

        # Extract usage
        tokens_in = 0
        tokens_out = 0
        if hasattr(api_response, "usage") and api_response.usage:
            usage = api_response.usage
            tokens_in = getattr(usage, "input_tokens", 0) or 0
            tokens_out = getattr(usage, "output_tokens", 0) or 0

        # Extract model name
        model = ""
        if hasattr(api_response, "model"):
            model = api_response.model or ""

        # Extract finish reason
        finish_reason = ""
        if hasattr(api_response, "status"):
            # Responses API uses status: "completed", "failed", etc.
            finish_reason = api_response.status or ""
        elif hasattr(api_response, "finish_reason"):
            finish_reason = api_response.finish_reason or ""

        # Build metadata
        metadata: Dict[str, Any] = dict(request_metadata or {})
        if hasattr(api_response, "id"):
            metadata["response_id"] = api_response.id
        if hasattr(api_response, "created_at"):
            metadata["created_at"] = api_response.created_at

        return LLMResponse(
            text=text,
            finish_reason=finish_reason,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
            provider=provider,
            latency_ms=latency_ms,
            metadata=metadata,
        )

    @staticmethod
    def from_stream_event(
        event: Any,
        provider: str = "openai",
    ) -> Optional[LLMStreamChunk]:
        """Map a streaming event to :class:`LLMStreamChunk`.

        Parameters
        ----------
        event:
            A single streaming event from the Responses API.
        provider:
            Provider name for attribution.

        Returns
        -------
        Optional[LLMStreamChunk]
            A stream chunk, or None if the event should be skipped.
        """
        # Responses API streaming events
        event_type = getattr(event, "type", "")

        if event_type in {"response.output_text.delta", "response.output_text.delta"}:
            delta = getattr(event, "delta", "")
            return LLMStreamChunk(
                delta=delta,
                metadata={"event_type": event_type},
            )

        if event_type == "response.output_text.done":
            return LLMStreamChunk(
                delta="",
                finished=True,
                metadata={"event_type": event_type},
            )

        if event_type == "response.completed":
            # Final event — extract usage
            response = getattr(event, "response", None)
            tokens_out = 0
            if response and hasattr(response, "usage") and response.usage:
                tokens_out = getattr(response.usage, "output_tokens", 0) or 0

            finish_reason = ""
            if response and hasattr(response, "status"):
                finish_reason = response.status or ""

            return LLMStreamChunk(
                delta="",
                finish_reason=finish_reason,
                tokens_out=tokens_out,
                metadata={"event_type": event_type},
            )

        # Skip other event types
        return None