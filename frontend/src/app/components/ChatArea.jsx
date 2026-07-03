'use client';
import { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { fetchKeys, saveKey } from '../services/api';
import MessageBubble from './MessageBubble';
import ToolCard from './ToolCard';

export default function ChatArea() {
  const { state, dispatch } = useApp();
  const containerRef = useRef(null);
  const bottomRef = useRef(null);
  const sessionId = 'single_session';
  const messages = state.messages[sessionId] || [];
  const [prevLength, setPrevLength] = useState(0);
  const [isTauri, setIsTauri] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.__TAURI_INTERNALS__) {
      setIsTauri(true);
    }
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const isNewMessage = messages.length > prevLength;
    setPrevLength(messages.length);

    if (isNewMessage) {
      // Smooth scroll to bottom on new messages (starts of turns)
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    } else {
      // During token streaming, only scroll down if the user is already near the bottom.
      // This prevents interrupting the user if they've scrolled up to read something.
      const threshold = 150; // pixels from bottom
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;
      if (isNearBottom) {
        bottomRef.current?.scrollIntoView({ behavior: 'auto' });
      }
    }
  }, [messages, prevLength]);

  function handleRetry() {
    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user');
    if (!lastUserMsg) return;

    dispatch({ type: 'REMOVE_LAST_ASSISTANT', sessionId });
    dispatch({ type: 'SET_RETRY', payload: { sessionId, message: lastUserMsg.content } });
  }

  function findLastAssistantIndex() {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant') return i;
    }
    return -1;
  }

  const lastAssistantIdx = findLastAssistantIndex();

  const [isHfConfigured, setIsHfConfigured] = useState(true);
  const [hfKeyInput, setHfKeyInput] = useState('');
  const [savingHf, setSavingHf] = useState(false);

  useEffect(() => {
    checkHfKey();
  }, []);

  async function checkHfKey() {
    try {
      const k = await fetchKeys();
      if (k.HUGGINGFACE_API_KEY && k.HUGGINGFACE_API_KEY.configured) {
        setIsHfConfigured(true);
      } else {
        setIsHfConfigured(false);
      }
    } catch {}
  }

  async function handleSaveHfKey(e) {
    e.preventDefault();
    if (!hfKeyInput.trim()) return;
    setSavingHf(true);
    try {
      await saveKey('HUGGINGFACE_API_KEY', hfKeyInput.trim());
      setIsHfConfigured(true);
    } catch {}
    setSavingHf(false);
  }

  function handleStarterPrompt(messageText) {
    // 1. Add user bubble to the screen
    dispatch({
      type: 'ADD_MESSAGE',
      sessionId: 'single_session',
      payload: { id: 'msg_' + Date.now(), role: 'user', content: messageText }
    });
    // 2. Trigger sending via InputBar listener
    dispatch({
      type: 'SET_RETRY',
      payload: { sessionId: 'single_session', message: messageText }
    });
  }

  function handleChoice(msgId, choice, messageText) {
    // Update the choice card state to reflect selection
    dispatch({
      type: 'UPDATE_MESSAGE_PROPS',
      sessionId: 'single_session',
      messageId: msgId,
      payload: { pending: false, choice }
    });

    if (choice === 'parallel') {
      // Trigger parallel stream
      dispatch({
        type: 'SET_RETRY',
        payload: { sessionId: 'single_session', message: messageText, runParallel: true }
      });
    } else {
      // Queue the task
      dispatch({
        type: 'ADD_TO_QUEUE',
        payload: { id: 'queued_' + Date.now(), content: messageText }
      });
      dispatch({
        type: 'ADD_MESSAGE',
        sessionId: 'single_session',
        payload: { role: 'system_notice', content: `⏳ Added to queue: "${messageText}"` }
      });
    }
  }

  if (messages.length === 0) {
    return (
      <div className="welcome-screen">
        {/* PREMIUM CREATOR LOGO BADGE */}
        <a 
          href="https://divyansh-tiwari.xyz/" 
          target="_blank" 
          rel="noopener noreferrer"
          style={{
            textDecoration: 'none',
            display: 'inline-flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '20px',
            transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
            cursor: 'pointer'
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'scale(1.08)';
            const badge = e.currentTarget.querySelector('.dt-badge-logo');
            if (badge) {
              badge.style.boxShadow = '0 0 25px rgba(6, 182, 212, 0.5)';
              badge.style.borderColor = 'var(--accent-cyan)';
            }
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'scale(1)';
            const badge = e.currentTarget.querySelector('.dt-badge-logo');
            if (badge) {
              badge.style.boxShadow = '0 0 15px rgba(6, 182, 212, 0.2)';
              badge.style.borderColor = 'rgba(6, 182, 212, 0.3)';
            }
          }}
        >
          <div 
            className="dt-badge-logo"
            style={{
              width: '140px',
              height: '140px',
              borderRadius: '28px',
              background: 'linear-gradient(135deg, rgba(13, 17, 23, 0.9) 0%, rgba(20, 26, 35, 0.9) 100%)',
              border: '2px solid rgba(6, 182, 212, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 25px rgba(6, 182, 212, 0.25)',
              transition: 'all 0.3s ease',
              overflow: 'hidden'
            }}
          >
            <img 
              src="/devops_agent_thumbnail.png" 
              alt="DevOps Concierge Logo"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                borderRadius: '24px'
              }}
            />
          </div>
          <span style={{
            fontSize: '12px',
            fontWeight: '600',
            color: 'var(--accent-cyan)',
            letterSpacing: '1px',
            textTransform: 'uppercase',
            background: 'rgba(6, 182, 212, 0.08)',
            padding: '4px 10px',
            borderRadius: '20px',
            border: '1px solid rgba(6, 182, 212, 0.15)'
          }}>
            Creator Portfolio ↗
          </span>
        </a>

        <h1>DevOps Concierge Agent</h1>
        <p style={{ maxWidth: '580px', margin: '0 auto 8px auto' }}>
          I can scaffold projects, select databases, push to GitHub, deploy to Vercel,
          and generate business documentation — all through conversation.
        </p>
        <p style={{ 
          fontSize: '13px', 
          color: 'var(--text-muted)', 
          margin: '0 0 24px 0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '5px'
        }}>
          Designed & Engineered by 
          <a 
            href="https://divyansh-tiwari.xyz/" 
            target="_blank" 
            rel="noopener noreferrer"
            style={{ 
              color: '#fff', 
              textDecoration: 'underline', 
              fontWeight: '600',
              transition: 'color 0.2s' 
            }}
            onMouseEnter={e => e.target.style.color = 'var(--accent-cyan)'}
            onMouseLeave={e => e.target.style.color = '#fff'}
          >
            Divyansh Tiwari
          </a>
        </p>
        
        {!isTauri && (
          <div className="desktop-download-box" style={{
            margin: '24px auto 0 auto',
            maxWidth: '580px',
            background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%)',
            border: '1px solid rgba(6, 182, 212, 0.25)',
            borderRadius: '16px',
            padding: '16px 20px',
            boxShadow: '0 8px 32px rgba(6, 182, 212, 0.1)',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>🖥️</span>
              <span style={{
                fontFamily: '"Outfit", sans-serif',
                fontWeight: '700',
                fontSize: '15px',
                color: '#fff',
                letterSpacing: '-0.3px'
              }}>
                Get DevOps Concierge for Windows
              </span>
            </div>
            <p style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              margin: 0,
              lineHeight: '1.5',
              maxWidth: '450px'
            }}>
              Download the standalone desktop app to automatically manage backend microservices, bypass CORS limits, and integrate natively with your local file system.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
              <div style={{ display: 'flex', gap: '12px' }}>
                <a 
                  href="https://github.com/divyansh2102t-dev/DevOps-Concierge-Agent/releases/download/v0.1.0/devops-concierge_0.1.0_x64-setup.exe"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    textDecoration: 'none',
                    background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
                    color: '#fff',
                    fontSize: '12px',
                    fontWeight: '600',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    boxShadow: '0 4px 14px rgba(6, 182, 212, 0.4)',
                    transition: 'all 0.2s ease',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = '0 6px 20px rgba(6, 182, 212, 0.6)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 4px 14px rgba(6, 182, 212, 0.4)';
                  }}
                >
                  📥 Download for Windows
                </a>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Are you an IT admin? Download the <a href="https://github.com/divyansh2102t-dev/DevOps-Concierge-Agent/releases/download/v0.1.0/devops-concierge_0.1.0_x64_en-US.msi" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-cyan)', textDecoration: 'underline' }}>MSI Installer (.msi)</a> instead.
              </div>
            </div>
          </div>
        )}

        <div className="welcome-cards" style={{ marginTop: '30px' }}>
          <div className="welcome-card" style={{ cursor: 'default' }}>
            <h3>🏗️ Scaffold Project</h3>
            <p>Create a Next.js app with database setup</p>
          </div>
          <div className="welcome-card" style={{ cursor: 'default' }}>
            <h3>🚀 Deploy to Cloud</h3>
            <p>Push to GitHub and deploy to Vercel</p>
          </div>
          <div className="welcome-card" style={{ cursor: 'default' }}>
            <h3>📄 Generate Docs</h3>
            <p>Create PPTX, DOCX, and diagrams</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="messages-container" ref={containerRef}>
      {messages.map((msg, i) => {
        if (msg.role === 'tool') {
          return <ToolCard key={i} data={msg} />;
        }
        if (msg.role === 'system_notice') {
          return (
            <div key={i} className={`queue-notice ${msg.content.includes('Starting') ? 'starting' : ''}`}>
              <span>{msg.content.includes('Starting') ? '🚀' : '⏳'}</span>
              <div>{msg.content}</div>
            </div>
          );
        }
        if (msg.role === 'system_choice') {
          return (
            <div key={i} className="system-choice-card">
              <div className="system-choice-header">
                <span className="system-choice-icon">⚡</span>
                <span className="system-choice-title">Parallel Task Orchestrator</span>
              </div>
              <p className="system-choice-desc">
                An operation is currently running. Would you like to execute this task in parallel, or queue it to run sequentially after the active task finishes?
                <br/>
                <strong style={{ color: 'var(--text-primary)', marginTop: '8px', display: 'block' }}>
                  Task: "{msg.content}"
                </strong>
              </p>
              {msg.pending ? (
                <div className="system-choice-buttons">
                  <button 
                    className="system-choice-btn parallel"
                    onClick={() => handleChoice(msg.id, 'parallel', msg.content)}
                  >
                    ⚡ Run in Parallel
                  </button>
                  <button 
                    className="system-choice-btn queue"
                    onClick={() => handleChoice(msg.id, 'queue', msg.content)}
                  >
                    ⏳ Queue Task
                  </button>
                </div>
              ) : (
                <div className="queue-notice" style={{ borderLeftColor: msg.choice === 'parallel' ? 'var(--accent-cyan)' : 'var(--accent-amber)' }}>
                  {msg.choice === 'parallel' ? '🚀 Running in parallel...' : '⏳ Added to sequential queue.'}
                </div>
              )}
            </div>
          );
        }
        return (
          <MessageBubble
            key={i}
            message={msg}
            isLast={msg.role === 'assistant' && i === lastAssistantIdx}
            onRetry={handleRetry}
            isStreaming={state.isStreaming}
          />
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
