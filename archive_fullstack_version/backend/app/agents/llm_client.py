"""
Shared LLM client with tool-use execution loop.

Supports multiple providers:
  - Anthropic Claude (LLM_PROVIDER=anthropic)
  - Google Gemini   (LLM_PROVIDER=gemini)

This is the only file that touches provider SDKs directly.
All agents use this via BaseAgent — they never import provider SDKs themselves.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

ToolDefinition = dict[str, Any]
ToolResult = dict[str, Any]


class LLMResponse:
    """Wraps the final LLM response with extracted text and token counts."""

    def __init__(
        self,
        content: str,
        tokens_in: int,
        tokens_out: int,
        stop_reason: str,
    ) -> None:
        self.content = content
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.stop_reason = stop_reason

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


# ── Anthropic Client ──────────────────────────────────────────────────────────

class AnthropicLLMClient:
    """Anthropic Claude client with full tool-use loop support."""

    def __init__(self) -> None:
        import anthropic
        from tenacity import (
            retry,
            retry_if_exception_type,
            stop_after_attempt,
            wait_exponential,
        )
        if not settings.ANTHROPIC_API_KEY:
            raise LLMError(message="ANTHROPIC_API_KEY is not configured.")
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._anthropic = anthropic
        logger.info("llm_client_initialized", model=settings.LLM_MODEL, provider="anthropic")

    async def run_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[ToolDefinition],
        tool_executor: Callable[[str, dict], Any],
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, Any], None] | None = None,
    ) -> LLMResponse:
        import asyncio

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        total_tokens_in = 0
        total_tokens_out = 0
        iteration = 0
        max_iterations = 15

        while iteration < max_iterations:
            iteration += 1

            response = await asyncio.to_thread(
                self._client.messages.create,
                model=settings.LLM_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )

            total_tokens_in += response.usage.input_tokens
            total_tokens_out += response.usage.output_tokens

            logger.debug(
                "llm_response",
                stop_reason=response.stop_reason,
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
                iteration=iteration,
            )

            if response.stop_reason == "end_turn":
                text = self._extract_text(response.content)
                return LLMResponse(
                    content=text,
                    tokens_in=total_tokens_in,
                    tokens_out=total_tokens_out,
                    stop_reason="end_turn",
                )

            if response.stop_reason == "tool_use":
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tool_block in tool_use_blocks:
                    tool_name = tool_block.name
                    tool_input = tool_block.input

                    if on_tool_call:
                        on_tool_call(tool_name, tool_input)

                    try:
                        result = await asyncio.to_thread(tool_executor, tool_name, tool_input)
                        result_str = (
                            json.dumps(result, default=str)
                            if not isinstance(result, str)
                            else result
                        )
                        is_error = False
                    except Exception as exc:
                        result_str = f"Tool execution error: {exc}"
                        is_error = True
                        logger.warning("tool_execution_error", tool=tool_name, error=str(exc))

                    if on_tool_result:
                        on_tool_result(tool_name, result_str)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": result_str,
                        "is_error": is_error,
                    })

                messages.append({"role": "user", "content": tool_results})
            else:
                text = self._extract_text(response.content)
                return LLMResponse(
                    content=text,
                    tokens_in=total_tokens_in,
                    tokens_out=total_tokens_out,
                    stop_reason=response.stop_reason,
                )

        raise LLMError(
            message=f"Tool-use loop exceeded {max_iterations} iterations."
        )

    @staticmethod
    def _extract_text(content: list) -> str:
        parts = [b.text for b in content if hasattr(b, "text")]
        return "\n".join(parts).strip()


# ── Gemini Client ─────────────────────────────────────────────────────────────

class GeminiLLMClient:
    """
    Google Gemini client with function-calling loop support.

    Uses the current `google-genai` SDK (≥ 1.0).  The deprecated
    `google-generativeai` SDK has been removed.

    Free tier: gemini-2.0-flash (15 RPM, 1M TPM, 1500 RPD)
    Converts Anthropic-style tool definitions to Gemini format automatically.

    Install:
        pip install google-genai>=1.0.0
    """

    def __init__(self) -> None:
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError:
            raise LLMError(
                message="google-genai package not installed. "
                        "Run: pip install 'google-genai>=1.0.0'"
            )
        if not settings.GEMINI_API_KEY:
            raise LLMError(message="GEMINI_API_KEY is not configured.")

        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._types = genai_types
        logger.info("llm_client_initialized", model=settings.LLM_MODEL, provider="gemini")

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[Any]:
        """
        Convert Anthropic-style tool definitions to google-genai Tool objects.

        Anthropic input format:
            {"name": ..., "description": ..., "input_schema": {JSON Schema}}

        Converted to:
            types.Tool(function_declarations=[types.FunctionDeclaration(...)])
        """
        declarations = []
        for tool in tools:
            schema = dict(tool.get("input_schema", {}))
            # Gemini rejects 'additionalProperties' — strip it recursively
            schema.pop("additionalProperties", None)
            if "properties" in schema:
                for prop_val in schema["properties"].values():
                    if isinstance(prop_val, dict):
                        prop_val.pop("additionalProperties", None)

            declarations.append(
                self._types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    parameters=schema,
                )
            )
        return [self._types.Tool(function_declarations=declarations)]

    def _call_api(
        self,
        contents: list[Any],
        gemini_tools: list[Any],
        system_instruction: str,
        max_retries: int = 5,
    ) -> Any:
        """
        Call `client.models.generate_content` with 429-aware retry logic.

        The free tier allows 15 RPM. With 4 sequential agents each making
        multiple tool calls, we can burst past that limit. Retry strategy:
          1. Parse "retry in Xs" hint from the error message
          2. Sleep for that duration (+ 2s buffer), capped at 90s
          3. Fall back to exponential backoff when no hint is present
        """
        config = self._types.GenerateContentConfig(
            tools=gemini_tools,
            system_instruction=system_instruction,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
        )

        delay = 5.0
        for attempt in range(max_retries + 1):
            try:
                return self._client.models.generate_content(
                    model=settings.LLM_MODEL,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                exc_str = str(exc)
                is_rate_limit = (
                    "429" in exc_str
                    or "quota" in exc_str.lower()
                    or "ResourceExhausted" in type(exc).__name__
                    or "rate" in exc_str.lower()
                )
                if not is_rate_limit or attempt >= max_retries:
                    raise

                m = re.search(
                    r"retry in (\d+(?:\.\d+)?)\s*(ms|s)\b",
                    exc_str,
                    re.IGNORECASE,
                )
                if m:
                    wait = float(m.group(1))
                    if m.group(2).lower() == "ms":
                        wait /= 1000.0
                    wait = min(wait + 2.0, 90.0)
                else:
                    wait = min(delay, 90.0)
                    delay *= 2.0

                logger.warning(
                    "gemini_rate_limit_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_seconds=round(wait, 1),
                    error=exc_str[:200],
                )
                time.sleep(wait)

        raise LLMError(message="Gemini rate limit: max retries exceeded.")

    async def run_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[ToolDefinition],
        tool_executor: Callable[[str, dict], Any],
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, Any], None] | None = None,
    ) -> LLMResponse:
        import asyncio

        gemini_tools = self._convert_tools(tools)
        types = self._types

        # Maintain conversation as a list of Content objects (new SDK pattern)
        contents: list[Any] = [
            types.Content(
                role="user",
                parts=[types.Part(text=user_message)],
            )
        ]

        total_tokens_in = 0
        total_tokens_out = 0
        iteration = 0
        max_iterations = 15

        while iteration < max_iterations:
            iteration += 1

            response = await asyncio.to_thread(
                self._call_api, contents, gemini_tools, system_prompt
            )

            # Accumulate token counts
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                total_tokens_in += response.usage_metadata.prompt_token_count or 0
                total_tokens_out += response.usage_metadata.candidates_token_count or 0

            logger.debug(
                "llm_response",
                provider="gemini",
                iteration=iteration,
                tokens_in=total_tokens_in,
                tokens_out=total_tokens_out,
            )

            # Extract parts from the first candidate
            candidate = response.candidates[0]
            parts = candidate.content.parts if candidate.content else []

            function_calls = []
            text_parts = []
            for part in parts:
                if part.function_call and part.function_call.name:
                    function_calls.append(part.function_call)
                elif part.text:
                    text_parts.append(part.text)

            # No function calls → final answer
            if not function_calls:
                return LLMResponse(
                    content="\n".join(text_parts).strip(),
                    tokens_in=total_tokens_in,
                    tokens_out=total_tokens_out,
                    stop_reason="end_turn",
                )

            # Append model turn to conversation
            contents.append(candidate.content)

            # Execute tool calls, build function-response turn
            response_parts = []
            for fc in function_calls:
                tool_name = fc.name
                tool_input = dict(fc.args)

                logger.debug("tool_call", tool=tool_name, input_keys=list(tool_input.keys()))

                if on_tool_call:
                    on_tool_call(tool_name, tool_input)

                try:
                    result = await asyncio.to_thread(tool_executor, tool_name, tool_input)
                    result_data = (
                        result if isinstance(result, dict)
                        else {"result": str(result)}
                    )
                except Exception as exc:
                    result_data = {"error": str(exc)}
                    logger.warning("tool_execution_error", tool=tool_name, error=str(exc))

                if on_tool_result:
                    on_tool_result(tool_name, json.dumps(result_data, default=str))

                response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name,
                            response={"result": result_data},
                        )
                    )
                )

            # Append tool responses as a user turn
            contents.append(
                types.Content(role="user", parts=response_parts)
            )

        raise LLMError(
            message=f"Tool-use loop exceeded {max_iterations} iterations."
        )


# ── Factory / Singleton ───────────────────────────────────────────────────────

# Type alias for either client
LLMClient = AnthropicLLMClient | GeminiLLMClient

_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """
    Return a cached LLM client instance.

    Selects provider based on LLM_PROVIDER setting:
      - "anthropic" → AnthropicLLMClient
      - "gemini"    → GeminiLLMClient
    """
    global _llm_client
    if _llm_client is None:
        provider = settings.LLM_PROVIDER.lower()
        if provider == "anthropic":
            _llm_client = AnthropicLLMClient()
        elif provider == "gemini":
            _llm_client = GeminiLLMClient()
        else:
            raise LLMError(
                message=f"Unknown LLM_PROVIDER '{provider}'. "
                        "Use 'anthropic' or 'gemini'."
            )
    return _llm_client
