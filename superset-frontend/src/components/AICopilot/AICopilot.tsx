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

import { type FC, useCallback, useEffect, useRef, useState } from 'react';
import { css } from '@emotion/react';
import { t } from '@apache-superset/core/translation';
import { Button, Input, Tag, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloseOutlined,
  DeleteOutlined,
  LoadingOutlined,
  MinusOutlined,
  RobotOutlined,
  SendOutlined,
  ExpandOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useCopilotChat } from './useCopilotChat';
import type { ChatMessage, StepInfo } from './types';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

/* ------------------------------------------------------------------ */
/* Styles                                                              */
/* ------------------------------------------------------------------ */

const overlayStyle = css`
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1050;
  font-family: inherit;
`;

const panelStyle = css`
  width: 440px;
  height: 580px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow:
    0 6px 16px rgba(0, 0, 0, 0.12),
    0 3px 6px rgba(0, 0, 0, 0.08);
  overflow: hidden;
`;

const maximizedStyle = css`
  width: 900px;
  height: 92vh;
`;

const headerStyle = css`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(135deg, #1677ff 0%, #4096ff 100%);
  color: #fff;
  user-select: none;
`;

const messagesStyle = css`
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const inputAreaStyle = css`
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 8px;
  align-items: flex-end;
`;

const userBubbleStyle = css`
  align-self: flex-end;
  background: #e6f4ff;
  border-radius: 12px 12px 4px 12px;
  padding: 8px 12px;
  max-width: 85%;
  word-break: break-word;
`;

const assistantBubbleStyle = css`
  align-self: flex-start;
  background: #fafafa;
  border-radius: 12px 12px 12px 4px;
  padding: 8px 12px;
  max-width: 90%;
  word-break: break-word;
`;

const errorBubbleStyle = css`
  border: 1px solid #ff4d4f;
  background: #fff2f0;
`;

const metaRowStyle = css`
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 4px;
`;

const stepRowStyle = css`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
  font-size: 12px;
`;

const stepsContainerStyle = css`
  margin: 6px 0;
  padding: 8px 10px;
  background: #f6f8fa;
  border-radius: 8px;
  border-left: 3px solid #1677ff;
`;

const fabStyle = css`
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1677ff 0%, #4096ff 100%);
  color: #fff;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.4);
  border: none;
  transition: transform 0.2s;
  &:hover {
    transform: scale(1.08);
  }
`;

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

const StepIcon: FC<{ step: StepInfo }> = ({ step }) => {
  if (step.status === 'error')
    return <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 13 }} />;
  if (step.status === 'done')
    return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 13 }} />;
  if (step.type === 'search')
    return <SearchOutlined style={{ color: '#1677ff', fontSize: 13 }} />;
  if (step.type === 'tool_call')
    return <ToolOutlined style={{ color: '#faad14', fontSize: 13 }} />;
  if (step.type === 'thinking')
    return <ThunderboltOutlined style={{ color: '#1677ff', fontSize: 13 }} />;
  return <LoadingOutlined style={{ fontSize: 13 }} />;
};

const StepDisplay: FC<{ step: StepInfo }> = ({ step }) => (
  <div css={stepRowStyle}>
    <StepIcon step={step} />
    <Text strong style={{ fontSize: 12 }}>{step.tool}</Text>
    <Text type="secondary" style={{ fontSize: 11 }}>{step.detail}</Text>
    {step.status === 'done' && (
      <Tag color="green" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>
        Done
      </Tag>
    )}
    {step.status === 'error' && (
      <Tag color="red" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>
        Error
      </Tag>
    )}
  </div>
);

const StepsPanel: FC<{ steps: StepInfo[] }> = ({ steps }) => {
  if (!steps || steps.length === 0) return null;

  // Group by unique tool calls (skip thinking bookends)
  const toolSteps = steps.filter(s => s.type !== 'thinking');

  return (
    <div css={stepsContainerStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
        <ToolOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />
        <Text type="secondary" style={{ fontSize: 11 }}>
          {toolSteps.length > 0
            ? `Used ${toolSteps.length} tool${toolSteps.length > 1 ? 's' : ''}`
            : 'Processing...'}
        </Text>
      </div>
      {steps.map((step, idx) => (
        <StepDisplay key={`${step.tool}-${idx}`} step={step} />
      ))}
    </div>
  );
};

const IntentMeta: FC<{ domain?: string; intent?: string; elapsedMs?: number }> = ({
  domain,
  intent,
  elapsedMs,
}) => {
  if (!domain && !intent) return null;
  return (
    <div css={metaRowStyle}>
      {domain && <Tag color="blue">{domain}</Tag>}
      {intent && <Tag color="green">{intent}</Tag>}
      {elapsedMs !== undefined && (
        <Text type="secondary" style={{ fontSize: 11 }}>
          {(elapsedMs / 1000).toFixed(1)}s
        </Text>
      )}
    </div>
  );
};

const MessageBubble: FC<{ message: ChatMessage }> = ({ message }) => {
  if (message.isLoading) {
    return (
      <div css={assistantBubbleStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <LoadingOutlined style={{ color: '#1677ff' }} />
          <Text type="secondary">{t('Agent is working...')}</Text>
        </div>
      </div>
    );
  }

  const isUser = message.role === 'user';
  const bubbleCss = [
    isUser ? userBubbleStyle : assistantBubbleStyle,
    message.isError ? errorBubbleStyle : undefined,
  ];

  return (
    <div css={bubbleCss}>
      {!isUser && (
        <>
          <IntentMeta
            domain={message.domain}
            intent={message.intent}
            elapsedMs={message.elapsedMs}
          />
          <StepsPanel steps={message.steps || []} />
        </>
      )}
      <Paragraph
        style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 13 }}
      >
        {message.content}
      </Paragraph>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

const AICopilot: FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, isLoading, sendMessage, clearHistory } = useCopilotChat();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(() => {
    if (inputValue.trim()) {
      sendMessage(inputValue.trim());
      setInputValue('');
    }
  }, [inputValue, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  if (!isOpen) {
    return (
      <div css={overlayStyle}>
        <button
          css={fabStyle}
          onClick={() => setIsOpen(true)}
          aria-label={t('Open AI Copilot')}
          type="button"
        >
          <RobotOutlined />
        </button>
      </div>
    );
  }

  return (
    <div css={overlayStyle}>
      <div css={[panelStyle, isMaximized && maximizedStyle]}>
        {/* Header */}
        <div css={headerStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <RobotOutlined style={{ fontSize: 18 }} />
            <Text strong style={{ color: '#fff', fontSize: 14 }}>
              {t('AI Copilot')}
            </Text>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <Button
              type="text"
              size="small"
              icon={<DeleteOutlined />}
              onClick={clearHistory}
              style={{ color: '#fff' }}
              title={t('Clear history')}
            />
            <Button
              type="text"
              size="small"
              icon={isMaximized ? <MinusOutlined /> : <ExpandOutlined />}
              onClick={() => setIsMaximized(prev => !prev)}
              style={{ color: '#fff' }}
              title={isMaximized ? t('Minimize') : t('Maximize')}
            />
            <Button
              type="text"
              size="small"
              icon={<CloseOutlined />}
              onClick={() => setIsOpen(false)}
              style={{ color: '#fff' }}
              title={t('Close')}
            />
          </div>
        </div>

        {/* Messages */}
        <div css={messagesStyle}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', marginTop: 40 }}>
              <RobotOutlined style={{ fontSize: 48, color: '#bfbfbf' }} />
              <Paragraph type="secondary" style={{ marginTop: 16 }}>
                {t('Ask me to create dashboards, charts, or explore data.')}
              </Paragraph>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 12 }}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {t('Try:')}
                </Text>
                <Tag style={{ cursor: 'pointer', textAlign: 'center' }}>
                  &quot;Create a dashboard with 3 charts from the examples database&quot;
                </Tag>
                <Tag style={{ cursor: 'pointer', textAlign: 'center' }}>
                  &quot;Show me all available datasets&quot;
                </Tag>
                <Tag style={{ cursor: 'pointer', textAlign: 'center' }}>
                  &quot;List my dashboards&quot;
                </Tag>
              </div>
            </div>
          )}
          {messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div css={inputAreaStyle}>
          <TextArea
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('Ask AI Copilot...')}
            autoSize={{ minRows: 1, maxRows: 3 }}
            disabled={isLoading}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={isLoading}
            disabled={!inputValue.trim()}
          />
        </div>
      </div>
    </div>
  );
};

export default AICopilot;

