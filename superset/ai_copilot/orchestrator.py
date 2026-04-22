# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Orchestrator using mcp_use + LangChain for agentic MCP tool execution.

Supports pluggable LLM providers via AI_COPILOT_LLM_PROVIDER:
  - "groq"   (default) — uses langchain_groq.ChatGroq
  - "openai"           — uses langchain_openai.ChatOpenAI
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, TypedDict

from superset.ai_copilot.config import get_copilot_config

logger = logging.getLogger(__name__)


class StepInfo(TypedDict):
    type: str          # "tool_call" | "tool_result" | "thinking" | "search"
    tool: str
    status: str        # "started" | "done" | "error"
    detail: str


class CopilotResponse(TypedDict):
    domain: str
    intent: str
    explanation: str
    steps: list[StepInfo]
    response: str
    elapsed_ms: int


class CopilotOrchestrator:
    """Orchestrate queries using mcp_use MCPAgent with a configurable LLM.

    Supports Groq (default) and OpenAI providers via the
    ``llm_provider`` config key.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.cfg = config or get_copilot_config()
        self._agent: Any | None = None
        self._client: Any | None = None

    def _create_llm(self) -> Any:
        """Create a LangChain chat model based on the configured provider."""
        provider = self.cfg.get("llm_provider", "groq").lower()
        max_tokens = self.cfg.get("max_tokens", 4096)
        temperature = self.cfg.get("temperature", 0.1)

        if provider == "openai":
            from langchain_openai import ChatOpenAI

            api_key = self.cfg.get("openai_api_key", "")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not configured. "
                    "Set it as an environment variable or in superset_config.py."
                )
            kwargs: dict[str, Any] = {
                "model": self.cfg.get("openai_model", "gpt-4o"),
                "api_key": api_key,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            base_url = self.cfg.get("openai_base_url")
            if base_url:
                kwargs["base_url"] = base_url
            return ChatOpenAI(**kwargs)

        # Default: Groq
        from langchain_groq import ChatGroq  # noqa: F811

        api_key = self.cfg.get("groq_api_key", "")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured. "
                "Set it as an environment variable or in superset_config.py."
            )
        return ChatGroq(
            model=self.cfg.get("groq_model", "llama-3.3-70b-versatile"),
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def _ensure_agent(self) -> Any:
        """Lazily create the MCPClient and MCPAgent."""
        if self._agent is not None:
            return self._agent

        from mcp_use import MCPAgent, MCPClient  # noqa: F811

        # Build config dict programmatically instead of from file so we can
        # pass the full parent-process environment to the MCP subprocess.
        # The MCP protocol's StdioServerParameters only inherits a small
        # safe-list of env vars by default, but the Superset MCP service
        # needs DATABASE_*, REDIS_*, PYTHONPATH, etc.
        mcp_config = {
            "mcpServers": {
                "superset": {
                    "command": "python",
                    "args": ["-m", "superset.mcp_service"],
                    "env": {**os.environ, "FASTMCP_TRANSPORT": "stdio"},
                }
            }
        }
        self._client = MCPClient(mcp_config)

        llm = self._create_llm()

        self._agent = MCPAgent(
            llm=llm,
            client=self._client,
            max_steps=self.cfg.get("mcp_agent_max_steps", 15),
            memory_enabled=True,
        )
        return self._agent

    async def _aprocess(self, query: str) -> CopilotResponse:
        """Async implementation of process_query."""
        start = time.monotonic()
        steps: list[StepInfo] = []

        if not self.cfg.get("groq_api_key") and not self.cfg.get("openai_api_key"):
            raise ValueError(
                "No LLM API key configured. Set GROQ_API_KEY or OPENAI_API_KEY "
                "as an environment variable or in superset_config.py."
            )

        agent = await self._ensure_agent()

        # Run the agent — it autonomously discovers and calls MCP tools
        steps.append(StepInfo(
            type="thinking",
            tool="agent",
            status="started",
            detail=f"Processing: {query[:80]}",
        ))

        try:
            response_text: str = await agent.run(query)
        except Exception as exc:
            logger.exception("MCPAgent run failed")
            steps.append(StepInfo(
                type="tool_call",
                tool="agent",
                status="error",
                detail=str(exc),
            ))
            response_text = f"Error: {exc}"

        # Extract steps from agent's conversation history if available
        steps.extend(_extract_steps_from_agent(agent))

        steps.append(StepInfo(
            type="thinking",
            tool="agent",
            status="done",
            detail="Response generated",
        ))

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Derive domain/intent from the conversation
        domain, intent = _infer_domain_intent(query)

        return CopilotResponse(
            domain=domain,
            intent=intent,
            explanation="",
            steps=steps,
            response=response_text,
            elapsed_ms=elapsed_ms,
        )

    def process_query(self, query: str) -> CopilotResponse:
        """Process a natural-language query end-to-end (sync wrapper)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in an async context — create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._aprocess(query))
                    return future.result(timeout=self.cfg.get("llm_timeout", 120))
            return loop.run_until_complete(self._aprocess(query))
        except RuntimeError:
            return asyncio.run(self._aprocess(query))

    async def close(self) -> None:
        """Clean up MCP sessions."""
        if self._client and hasattr(self._client, "close_all_sessions"):
            await self._client.close_all_sessions()
        self._agent = None
        self._client = None

    def clear_history(self) -> None:
        """Clear the agent's conversation memory."""
        if self._agent and hasattr(self._agent, "clear_conversation_history"):
            self._agent.clear_conversation_history()


def _extract_steps_from_agent(agent: Any) -> list[StepInfo]:
    """Extract tool call steps from the agent's internal state."""
    steps: list[StepInfo] = []
    try:
        # mcp_use MCPAgent stores steps in its history
        history = getattr(agent, "conversation_history", [])
        for msg in history:
            role = getattr(msg, "type", "") if hasattr(msg, "type") else ""
            content = getattr(msg, "content", "") or ""

            if role == "ai" and hasattr(msg, "tool_calls"):
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    steps.append(StepInfo(
                        type="tool_call",
                        tool=tool_name,
                        status="started",
                        detail=f"Calling {tool_name}",
                    ))
            elif role == "tool":
                tool_name = getattr(msg, "name", "unknown")
                truncated = content[:150] + "..." if len(content) > 150 else content
                steps.append(StepInfo(
                    type="tool_result",
                    tool=tool_name,
                    status="done",
                    detail=truncated,
                ))
    except Exception as exc:
        logger.debug("Could not extract agent steps: %s", exc)
    return steps


def _infer_domain_intent(query: str) -> tuple[str, str]:
    """Simple keyword-based domain/intent inference for metadata display."""
    q = query.lower()
    # Domain
    domain = "general"
    for kw, d in [
        ("sales", "sales"), ("revenue", "sales"), ("marketing", "marketing"),
        ("finance", "finance"), ("user", "users"), ("flight", "travel"),
        ("game", "gaming"),
    ]:
        if kw in q:
            domain = d
            break

    # Intent
    intent = "explore"
    for kw, i in [
        ("dashboard", "dashboard"), ("chart", "chart"), ("dataset", "dataset"),
        ("sql", "sql"), ("query", "sql"), ("list", "explore"),
        ("create", "chart"), ("build", "dashboard"), ("show", "explore"),
    ]:
        if kw in q:
            intent = i
            break

    return domain, intent
