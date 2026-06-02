"""
llm_provider.py — Provider abstraction layer.

Wraps the Anthropic and Google SDKs behind a common interface so the
agent loop doesn't need to know which one it's talking to.

Usage in agent.py:

    provider = get_provider(system_prompt)
    response = provider.start(question)

    while response.stop_reason == "tool_use":
        results = [execute_tool(tc.name, tc.args) for tc in response.tool_calls]
        response = provider.continue_with_tool_results(response.tool_calls, results)

    print(response.text)

Each provider manages its own message history internally.
"""

from __future__ import annotations

import time
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import anthropic
from google import genai
from google.genai import types as gtypes
from google.genai import errors as gerrors

from src.config import CONFIG
from src.tools import TOOLS_SCHEMA

# How long to wait before each retry attempt, in seconds.
# The free tier allows 5 requests per minute, so 60s is the minimum safe gap.
_RETRY_DELAYS = [60, 90, 120]


# --- data classes ---

@dataclass
class ToolCall:
    """Represents a single tool call requested by the model."""
    id: str    # used to match the result back to the call
    name: str  # e.g. "run_sql"
    args: dict # arguments to pass to the tool function


@dataclass
class LLMResponse:
    """Normalised response returned by both providers."""
    stop_reason: str                          # "tool_use" or "end_turn"
    text: str = ""                            # final answer text
    tool_calls: list[ToolCall] = field(default_factory=list)


# --- base class ---

class LLMProvider(ABC):
    """
    Interface that both providers implement.
    Each subclass manages its own internal message history.
    """

    @abstractmethod
    def start(self, question: str) -> LLMResponse:
        """Send the opening message and return the first response."""
        ...

    @abstractmethod
    def continue_with_tool_results(
        self,
        tool_calls: list[ToolCall],
        results: list[str],
    ) -> LLMResponse:
        """Send tool results back to the model and return the next response."""
        ...


# --- anthropic ---

class AnthropicProvider(LLMProvider):
    """Uses the Anthropic Messages API."""

    def __init__(self, system_prompt: str) -> None:
        self._client = anthropic.Anthropic(api_key=CONFIG.anthropic_api_key)
        self._system = system_prompt
        self._messages: list[dict] = []

    def _call(self) -> LLMResponse:
        """Send the current message history and return a normalised response."""
        response = self._client.messages.create(
            model=CONFIG.claude_model,
            max_tokens=4096,
            system=self._system,
            tools=TOOLS_SCHEMA,
            messages=self._messages,
        )

        self._messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return LLMResponse(stop_reason="end_turn", text=text)

        # Model wants to call one or more tools
        tool_calls = [
            ToolCall(id=b.id, name=b.name, args=b.input)
            for b in response.content
            if b.type == "tool_use"
        ]
        return LLMResponse(stop_reason="tool_use", tool_calls=tool_calls)

    def start(self, question: str) -> LLMResponse:
        self._messages = [{"role": "user", "content": question}]
        return self._call()

    def continue_with_tool_results(
        self,
        tool_calls: list[ToolCall],
        results: list[str],
    ) -> LLMResponse:
        # Anthropic expects all tool results in a single user turn
        tool_result_blocks = [
            {"type": "tool_result", "tool_use_id": tc.id, "content": result}
            for tc, result in zip(tool_calls, results)
        ]
        self._messages.append({"role": "user", "content": tool_result_blocks})
        return self._call()


# --- google ---

def _build_google_tools() -> gtypes.Tool:
    """Convert TOOLS_SCHEMA to the format the Google SDK expects."""
    declarations = []
    for tool in TOOLS_SCHEMA:
        props = {}
        for prop_name, prop_def in tool["input_schema"].get("properties", {}).items():
            props[prop_name] = gtypes.Schema(
                type=gtypes.Type.STRING,  # all tool arguments are strings
                description=prop_def.get("description", ""),
            )

        # Only set parameters if the tool actually takes arguments
        parameters = gtypes.Schema(
            type=gtypes.Type.OBJECT,
            properties=props,
            required=tool["input_schema"].get("required", []),
        ) if props else None

        declarations.append(
            gtypes.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=parameters,
            )
        )
    return gtypes.Tool(function_declarations=declarations)


class GoogleProvider(LLMProvider):
    """Uses the Google Gemini API (google-genai SDK)."""

    def __init__(self, system_prompt: str) -> None:
        self._client = genai.Client(api_key=CONFIG.google_api_key)
        self._system = system_prompt
        self._tools = _build_google_tools()
        self._contents: list[Any] = []

    def _make_config(self) -> gtypes.GenerateContentConfig:
        return gtypes.GenerateContentConfig(
            system_instruction=self._system,
            tools=[self._tools],
        )

    def _call(self) -> LLMResponse:
        """Send the current contents and return a normalised response.

        Retries automatically on 429 rate-limit errors. The retry delay is
        taken from the error message when available; otherwise falls back to
        the values in _RETRY_DELAYS.
        """
        next_delay: int | None = None  # populated from the error message

        for attempt in range(len(_RETRY_DELAYS) + 1):
            if attempt > 0:
                wait = next_delay if next_delay else _RETRY_DELAYS[attempt - 1]
                print(f"[GoogleProvider] rate limited — waiting {wait}s before retry {attempt}...")
                time.sleep(wait)
                next_delay = None

            try:
                response = self._client.models.generate_content(
                    model=CONFIG.gemini_model,
                    contents=self._contents,
                    config=self._make_config(),
                )
                break  # success — exit the retry loop
            except gerrors.ClientError as exc:
                if exc.code != 429 or attempt >= len(_RETRY_DELAYS):
                    raise  # not a rate-limit error, or retries exhausted

                # Pull the suggested wait time out of the error message if present
                match = re.search(r"retry in (\d+)", str(exc))
                if match:
                    next_delay = int(match.group(1)) + 5

        candidate = response.candidates[0]
        self._contents.append(candidate.content)

        # Check whether the model is requesting any function calls
        tool_calls = []
        for part in candidate.content.parts:
            if part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    id=fc.name,  # Gemini doesn't return unique call IDs
                    name=fc.name,
                    args=dict(fc.args),
                ))

        if tool_calls:
            return LLMResponse(stop_reason="tool_use", tool_calls=tool_calls)

        return LLMResponse(stop_reason="end_turn", text=response.text or "")

    def start(self, question: str) -> LLMResponse:
        self._contents = [
            gtypes.Content(role="user", parts=[gtypes.Part(text=question)])
        ]
        return self._call()

    def continue_with_tool_results(
        self,
        tool_calls: list[ToolCall],
        results: list[str],
    ) -> LLMResponse:
        # Google expects function responses as a user turn
        parts = [
            gtypes.Part.from_function_response(
                name=tc.name,
                response={"result": result},
            )
            for tc, result in zip(tool_calls, results)
        ]
        self._contents.append(gtypes.Content(role="user", parts=parts))
        return self._call()


# --- factory ---

def get_provider(system_prompt: str) -> LLMProvider:
    """Return the provider set in CONFIG.provider."""
    if CONFIG.provider == "anthropic":
        return AnthropicProvider(system_prompt)
    if CONFIG.provider == "google":
        return GoogleProvider(system_prompt)
    raise ValueError(f"Unknown provider: '{CONFIG.provider}'")
