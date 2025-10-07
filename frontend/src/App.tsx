import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  context?: ContextItem[];
}

interface ContextItem {
  conversation_id: number;
  scenario_title: string;
  matched_content: string;
  author_info: {
    name: string;
    type: string;
  };
  relevance_score: number;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showContext, setShowContext] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat/ask`, {
        content: input,
        conversation_history: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.answer,
        context: response.data.context_used,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '❌ Error: Could not get response. Please try again.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>🔧 Technical Support Assistant</h1>
        <p>Ask questions about technical issues - powered by historical Slack conversations</p>
      </header>

      <div className="chat-container">
        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-content">
                <strong>{msg.role === 'user' ? '👤 You' : '🤖 Assistant'}:</strong>
                <p>{msg.content}</p>
                
                {msg.context && msg.context.length > 0 && (
                  <div className="context-section">
                    <button
                      className="context-toggle"
                      onClick={() => setShowContext(showContext === idx ? null : idx)}
                    >
                      {showContext === idx ? '▼' : '▶'} View Context ({msg.context.length} items)
                    </button>
                    
                    {showContext === idx && (
                      <div className="context-items">
                        {msg.context.map((ctx, ctxIdx) => (
                          <div key={ctxIdx} className="context-item">
                            <div className="context-header">
                              <strong>{ctx.scenario_title}</strong>
                              <span className="relevance-score">
                                Relevance: {(ctx.relevance_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="context-body">
                              <em>
                                {ctx.author_info.name} ({ctx.author_info.type}):
                              </em>
                              <p>{ctx.matched_content.substring(0, 200)}...</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="message assistant loading">
              <div className="message-content">
                <strong>🤖 Assistant:</strong>
                <p className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </p>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about a technical issue..."
            rows={3}
            disabled={loading}
          />
          <button onClick={sendMessage} disabled={loading || !input.trim()}>
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>

      <footer className="app-footer">
        <p>
          💡 This assistant uses historical Slack conversations to provide context-aware answers
        </p>
      </footer>
    </div>
  );
}

export default App;