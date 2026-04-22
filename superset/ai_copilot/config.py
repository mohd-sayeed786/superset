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
"""AI Copilot configuration."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------
# LLM Provider: "groq" (default) or "openai"
# -----------------------------------------------------------------------
LLM_PROVIDER: str = os.environ.get("AI_COPILOT_LLM_PROVIDER", "groq")

# Groq configuration (default)
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# OpenAI configuration (placeholder — set these to switch provider)
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "")  # for Azure or proxies

# Shared LLM settings
LLM_MAX_TOKENS: int = int(os.environ.get("AI_COPILOT_MAX_TOKENS", "4096"))
LLM_TEMPERATURE: float = float(os.environ.get("AI_COPILOT_TEMPERATURE", "0.1"))

# MCP server config file path (JSON config for mcp_use)
MCP_CONFIG_PATH: str = os.environ.get(
    "MCP_CONFIG_PATH",
    str(Path(__file__).parent / "mcp_server_config.json"),
)

# Agent settings
MCP_AGENT_MAX_STEPS: int = int(os.environ.get("MCP_AGENT_MAX_STEPS", "15"))

# Timeouts (seconds)
LLM_TIMEOUT: int = int(os.environ.get("AI_COPILOT_LLM_TIMEOUT", "120"))

# Rate limiting
MAX_REQUESTS_PER_MINUTE: int = int(
    os.environ.get("AI_COPILOT_RATE_LIMIT", "20")
)


def get_copilot_config(app_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build copilot config from Flask app config with env-var fallbacks."""
    cfg = app_config or {}
    return {
        "llm_provider": cfg.get("AI_COPILOT_LLM_PROVIDER", LLM_PROVIDER),
        # Groq
        "groq_api_key": cfg.get("GROQ_API_KEY", GROQ_API_KEY),
        "groq_model": cfg.get("GROQ_MODEL", GROQ_MODEL),
        # OpenAI
        "openai_api_key": cfg.get("OPENAI_API_KEY", OPENAI_API_KEY),
        "openai_model": cfg.get("OPENAI_MODEL", OPENAI_MODEL),
        "openai_base_url": cfg.get("OPENAI_BASE_URL", OPENAI_BASE_URL),
        # Shared
        "max_tokens": cfg.get("AI_COPILOT_MAX_TOKENS", LLM_MAX_TOKENS),
        "temperature": cfg.get("AI_COPILOT_TEMPERATURE", LLM_TEMPERATURE),
        "mcp_config_path": cfg.get("MCP_CONFIG_PATH", MCP_CONFIG_PATH),
        "mcp_agent_max_steps": cfg.get("MCP_AGENT_MAX_STEPS", MCP_AGENT_MAX_STEPS),
        "llm_timeout": cfg.get("AI_COPILOT_LLM_TIMEOUT", LLM_TIMEOUT),
    }
