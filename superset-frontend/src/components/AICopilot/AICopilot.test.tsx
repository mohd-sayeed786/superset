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

import { render, screen, fireEvent, waitFor } from 'spec/helpers/testing-library';
import AICopilot from './AICopilot';

// Mock the API module
jest.mock('./api', () => ({
  queryCopilot: jest.fn(),
}));

const { queryCopilot } = jest.requireMock('./api');

test('renders the FAB button when closed', () => {
  render(<AICopilot />);
  expect(screen.getByLabelText('Open AI Copilot')).toBeInTheDocument();
});

test('opens the panel when FAB is clicked', () => {
  render(<AICopilot />);
  fireEvent.click(screen.getByLabelText('Open AI Copilot'));
  expect(screen.getByText('AI Copilot')).toBeInTheDocument();
  expect(
    screen.getByPlaceholderText('Ask AI Copilot...'),
  ).toBeInTheDocument();
});

test('shows empty state message when no messages', () => {
  render(<AICopilot />);
  fireEvent.click(screen.getByLabelText('Open AI Copilot'));
  expect(
    screen.getByText('Ask me to create dashboards, charts, or explore data.'),
  ).toBeInTheDocument();
});

test('sends a message and displays response', async () => {
  queryCopilot.mockResolvedValueOnce({
    domain: 'sales',
    intent: 'chart',
    explanation: 'Creating a chart',
    tool_results: [],
    response: 'Here is your chart!',
    elapsed_ms: 500,
  });

  render(<AICopilot />);
  fireEvent.click(screen.getByLabelText('Open AI Copilot'));

  const input = screen.getByPlaceholderText('Ask AI Copilot...');
  fireEvent.change(input, { target: { value: 'Show me sales chart' } });
  fireEvent.click(screen.getByRole('button', { name: '' })); // send button

  expect(screen.getByText('Show me sales chart')).toBeInTheDocument();

  await waitFor(() => {
    expect(screen.getByText('Here is your chart!')).toBeInTheDocument();
  });

  // Domain and intent tags should be visible
  expect(screen.getByText('sales')).toBeInTheDocument();
  expect(screen.getByText('chart')).toBeInTheDocument();
});

test('closes the panel when close button is clicked', () => {
  render(<AICopilot />);
  fireEvent.click(screen.getByLabelText('Open AI Copilot'));
  expect(screen.getByText('AI Copilot')).toBeInTheDocument();

  fireEvent.click(screen.getByTitle('Close'));
  expect(screen.getByLabelText('Open AI Copilot')).toBeInTheDocument();
});

