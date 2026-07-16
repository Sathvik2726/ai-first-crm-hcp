import React, { useState, useRef, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { sendChatMessage, addUserChatMessage } from '../store/interactionSlice';

export default function AIAssistant() {
  const dispatch = useDispatch();
  const { chatMessages, chatLoading, sessionId } = useSelector((state) => state.interaction);
  
  const [input, setInput] = useState('');
  const [showToolOutputs, setShowToolOutputs] = useState({}); // Keep track of toggled tool outputs
  
  const messageEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages, chatLoading]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || chatLoading) return;
    
    const userMessage = input.trim();
    setInput('');
    
    // Add user message to Redux
    dispatch(addUserChatMessage(userMessage));
    
    // Send to LangGraph API
    dispatch(sendChatMessage({ message: userMessage, sessionId }));
  };

  const toggleToolOutput = (index, toolIndex) => {
    const key = `${index}-${toolIndex}`;
    setShowToolOutputs((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleQuickAction = (text) => {
    setInput(text);
  };

  return (
    <div className="panel chat-panel" id="ai-chat-panel">
      <div className="panel-header">
        <h2>
          <span style={{ position: 'relative', display: 'inline-block' }}>
            🤖
            <span
              className="settings-indicator"
              style={{
                position: 'absolute',
                top: -2,
                right: -2,
                width: 6,
                height: 6,
                border: '1px solid black',
              }}
            ></span>
          </span>{' '}
          AI Assistant
        </h2>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          LangGraph Agent Active
        </span>
      </div>

      {/* Messages Window */}
      <div className="chat-messages" id="chat-messages-box">
        {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat-bubble ${msg.role === 'user' ? 'user' : 'ai'}`}
            id={`chat-message-${idx}`}
          >
            <div className="chat-bubble-header">
              <span>{msg.role === 'user' ? 'You' : 'Agent'}</span>
              <span>{msg.timestamp}</span>
            </div>
            
            {/* Message Body */}
            <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

            {/* Display Executed Tool Badges */}
            {msg.tool_calls && msg.tool_calls.length > 0 && (
              <div className="chat-tool-section">
                {msg.tool_calls.map((tc, tIdx) => {
                  const key = `${idx}-${tIdx}`;
                  const isVisible = !!showToolOutputs[key];
                  return (
                    <div key={tIdx} style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                      <button
                        type="button"
                        onClick={() => toggleToolOutput(idx, tIdx)}
                        className="tool-badge"
                        style={{ cursor: 'pointer' }}
                        id={`tool-badge-${idx}-${tIdx}`}
                      >
                        🔧 tool: {tc.tool} {isVisible ? '▲' : '▼'}
                      </button>
                      {isVisible && tc.result && (
                        <pre className="tool-output-preview" id={`tool-output-${idx}-${tIdx}`}>
                          {JSON.stringify(tc.result, null, 2)}
                        </pre>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
        {chatLoading && (
          <div className="chat-bubble ai" id="chat-bubble-loading">
            <div className="chat-bubble-header">
              <span>Agent</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="spinner"></span> Thinking and resolving tools...
            </div>
          </div>
        )}
        <div ref={messageEndRef} />
      </div>

      {/* Quick Action Suggestions */}
      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          marginBottom: '0.75rem',
          flexWrap: 'wrap',
          fontSize: '0.75rem',
        }}
      >
        <span style={{ color: 'var(--text-muted)', alignSelf: 'center' }}>Try:</span>
        <button
          type="button"
          onClick={() => handleQuickAction('Search for oncologist')}
          className="chip"
          style={{ cursor: 'pointer', background: 'rgba(99, 102, 241, 0.1)' }}
        >
          🔍 Search HCP
        </button>
        <button
          type="button"
          onClick={() =>
            handleQuickAction(
              'Met Dr. Amanda Smith, discussed OncoBoost dosing schedule, she was positive. Send Phase III PDF.'
            )
          }
          className="chip"
          style={{ cursor: 'pointer', background: 'rgba(99, 102, 241, 0.1)' }}
        >
          📝 Log Meeting
        </button>
        <button
          type="button"
          onClick={() => handleQuickAction('Show interaction history for Dr. Amanda Smith')}
          className="chip"
          style={{ cursor: 'pointer', background: 'rgba(99, 102, 241, 0.1)' }}
        >
          📜 View History
        </button>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="chat-input-container">
        <textarea
          placeholder="Describe interaction in natural language, ask questions, or edit logged entries..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend(e);
            }
          }}
          className="chat-input"
          id="chat-input-textarea"
          disabled={chatLoading}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={!input.trim() || chatLoading}
          id="chat-send-btn"
        >
          ➔
        </button>
      </form>
    </div>
  );
}
