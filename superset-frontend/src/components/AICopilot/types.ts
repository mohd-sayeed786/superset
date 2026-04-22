/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

/** Types for the AI Copilot chat interface. */

export interface StepInfo {
  type: 'tool_call' | 'tool_result' | 'thinking' | 'search';
  tool: string;
  status: 'started' | 'done' | 'error';
  detail: string;
}

export interface ToolResult {
  tool: string;
  success: boolean;
  result?: Record<string, unknown>;
  error?: string;
}

export interface CopilotApiResponse {
  domain: string;
  intent: string;
  explanation: string;
  steps: StepInfo[];
  response: string;
  elapsed_ms: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  domain?: string;
  intent?: string;
  explanation?: string;
  steps?: StepInfo[];
  elapsedMs?: number;
  isLoading?: boolean;
  isError?: boolean;
}
