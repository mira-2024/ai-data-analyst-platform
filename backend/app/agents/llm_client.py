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

    Free tier: gemini-2.0-flash (15 RPM, 1M TPM, 1500 RPD)
    Converts Anthropic-style tool definitions to Gemini format automatically.
    """

    def __init__(self) -> None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise LLMError(
                message="google-generativeai package not installed. "
                        "Run: pip install google-generativeai"
            )
        if not settings.GEMINI_API_KEY:
            raise LLMError(message="GEMINI_API_KEY is not configured.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._genai = genai
        logger.info("llm_client_initialized", model=settings.LLM_MODEL, provider="gemini")

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict]:
        """
        Convert Anthropic tool format to Gemini function declarations.

        Anthropic format:
            {"name": ..., "description": ..., "input_schema": {JSON Schema}}

        Gemini format:
            {"function_declarations": [{"name": ..., "description": ..., "parameters": {JSON Schema}}]}
        """
        function_declarations = []
        for tool in tools:
            schema = dict(tool.get("input_schema", {}))
            # Gemini does not use 'additionalProperties' — remove if present
            schema.pop("additionalProperties", None)
            # Ensure properties descriptions are strings (Gemini is strict)
            if "properties" in schema:
                for prop_name, prop_val in schema["properties"].items():
                    if isinstance(prop_val, dict):
                        prop_val.pop("additionalProperties", None)

            function_declarations.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": schema,
            })
        return [{"function_declarations": function_declarations}]

    @staticmethod
    def _send_with_retry(chat: Any, message: Any, max_retries: int = 5) -> Any:
        """
        Send a Gemini message, retrying on 429 rate-limit errors.

        The free tier allows 15 RPM. With 4 sequential agents each making
        multiple tool calls, we can burst past that limit. This method:
          1. Catches ResourceExhausted (HTTP 429) exceptions
          2. Parses the "retry in Xs" hint from the error message
          3. Sleeps for that duration (+ 2s buffer) then retries
          4. Falls back to exponential backoff if no hint is found
        """
        delay = 5.0  # Initial backoff in seconds
        for attempt in range(max_retries + 1):
            try:
                return chat.send_message(message)
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

                # Try to extract the suggested retry delay from the error message
                m = re.search(
                    r"retry in (\d+(?:\.\d+)?)\s*(ms|s)\b",
                    exc_str,
                    re.IGNORECASE,
                )
                if m:
                    wait = float(m.group(1))
                    if m.group(2).lower() == "ms":
                        wait /= 1000.0
                    wait = min(wait + 2.0, 90.0)   # add 2s buffer, cap at 90s
                else:
                    wait = min(delay, 90.0)
                    delay *= 2.0                    # exponential backoff

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

        model = self._genai.GenerativeModel(
            model_name=settings.LLM_MODEL,
            system_instruction=system_prompt,
            tools=gemini_tools,
        )

        chat = model.start_chat()

        total_tokens_in = 0
        total_tokens_out = 0
        iteration = 0
        max_iterations = 15

        # First message is the user string; subsequent messages are tool responses
        current_message: Any = user_message

        while iteration < max_iterations:
            iteration += 1

            # Use retry wrapper — free tier is 15 RPM and tool-heavy agents can hit it
            response = await asyncio.to_thread(
                self._send_with_retry, chat, current_message
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

            # Collect function calls and text parts
            function_calls = []
            text_parts = []

            for part in response.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    function_calls.append(part.function_call)
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

            # No function calls → final answer
            if not function_calls:
                return LLMResponse(
                    content="\n".join(text_parts).strip(),
                    tokens_in=total_tokens_in,
                    tokens_out=total_tokens_out,
                    stop_reason="end_turn",
                )

            # Execute all function calls and build response parts
            tool_response_parts = []
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

                tool_response_parts.append(
                    self._genai.protos.Part(
                        function_response=self._genai.protos.FunctionResponse(
                            name=tool_name,
                            response={"result": result_data},
                        )
                    )
                )

            # Send tool results back to Gemini
            current_message = tool_response_parts

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
