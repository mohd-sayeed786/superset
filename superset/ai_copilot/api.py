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
"""REST API for the AI Copilot feature."""
from __future__ import annotations

import logging
from typing import Any

from flask import request, Response
from flask_appbuilder.api import expose
from marshmallow import ValidationError

from superset.ai_copilot.config import get_copilot_config
from superset.ai_copilot.orchestrator import CopilotOrchestrator
from superset.ai_copilot.schemas import AICopilotQuerySchema, AICopilotResponseSchema
from superset.extensions import event_logger
from superset.views.base_api import BaseSupersetApi

logger = logging.getLogger(__name__)

query_schema = AICopilotQuerySchema()
response_schema = AICopilotResponseSchema()


class AICopilotRestApi(BaseSupersetApi):
    """AI Copilot REST API.

    Exposes ``POST /api/v1/ai/query`` which accepts a natural-language
    query, runs the mcp_use MCPAgent with Groq LLM, and returns
    a formatted response with step-by-step tool execution details.
    """

    resource_name = "ai"
    allow_browser_login = True
    class_permission_name = "AICopilot"

    openapi_spec_tag = "AI Copilot"

    _orchestrator: CopilotOrchestrator | None = None

    def _get_orchestrator(self) -> CopilotOrchestrator:
        if self._orchestrator is None:
            from flask import current_app

            cfg = get_copilot_config(current_app.config)
            self._orchestrator = CopilotOrchestrator(cfg)
        return self._orchestrator

    @expose("/query", methods=("POST",))
    @event_logger.log_this_with_context(log_to_statsd=False)
    def query(self) -> Response:
        """Process a natural-language query through the AI Copilot.
        ---
        post:
          summary: AI Copilot query
          description: >-
            Accepts a natural-language query, runs the MCP agent with Groq LLM,
            and returns a formatted response with tool execution steps.
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/AICopilotQuerySchema'
          responses:
            200:
              description: Copilot response
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/AICopilotResponseSchema'
            400:
              description: Invalid request
            500:
              description: Server error
        """
        try:
            body: dict[str, Any] = query_schema.load(request.json or {})
        except ValidationError as exc:
            return self.response_400(message=exc.messages)

        user_query: str = body["query"]
        logger.info("AI Copilot query: %s", user_query[:100])

        try:
            orchestrator = self._get_orchestrator()
            result = orchestrator.process_query(user_query)
            return self.response(200, **response_schema.dump(result))
        except ValueError as exc:
            logger.warning("AI Copilot config error: %s", exc)
            return self.response_400(message=str(exc))
        except Exception:
            logger.exception("AI Copilot query failed")
            return self.response_500(message="AI Copilot encountered an error")

