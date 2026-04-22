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
"""Marshmallow schemas for the AI Copilot API."""
from __future__ import annotations

from marshmallow import fields, Schema, validate


class AICopilotQuerySchema(Schema):
    """Request schema for POST /api/v1/ai/query."""

    query = fields.String(
        required=True,
        validate=validate.Length(min=1, max=2000),
        metadata={"description": "Natural-language query for the AI Copilot"},
    )


class StepInfoSchema(Schema):
    """Schema for individual agent execution steps."""

    type = fields.String()
    tool = fields.String()
    status = fields.String()
    detail = fields.String()


class ToolResultSchema(Schema):
    """Schema for individual MCP tool results (legacy)."""

    tool = fields.String()
    success = fields.Boolean()
    result = fields.Raw(allow_none=True)
    error = fields.String(allow_none=True)


class AICopilotResponseSchema(Schema):
    """Response schema for POST /api/v1/ai/query."""

    domain = fields.String()
    intent = fields.String()
    explanation = fields.String()
    steps = fields.List(fields.Nested(StepInfoSchema))
    response = fields.String()
    elapsed_ms = fields.Integer()
