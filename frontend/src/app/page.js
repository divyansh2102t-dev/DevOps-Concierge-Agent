'use client';
import { useState, useEffect } from 'react';
import { useApp } from './context/AppContext';
import ChatArea from './components/ChatArea';
import InputBar from './components/InputBar';
import SettingsPanel from './components/SettingsPanel';
import HistoryPanel from './components/HistoryPanel';
import CustomConfirmModal from './components/CustomConfirmModal';
import AuthorizationModal from './components/AuthorizationModal';
import AgentStatusBar from './components/AgentStatusBar';
import OnboardingModal from './components/OnboardingModal';
import TerminalPanel from './components/TerminalPanel';
import { API_BASE, deleteSession } from './services/api';

export default function Home() {
  const { state, dispatch } = useApp();
  const [confirmClearOpen, setConfirmClearOpen] = useState(false);

  // Poll terminals and active agents from the backend
  useEffect(() => {
    let intervalId;
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/chat/terminals`);
        if (res.ok) {
          const data = await res.json();
          dispatch({ type: 'SET_TERMINALS', payload: data.terminals || [] });
          dispatch({ type: 'SET_ACTIVE_AGENTS', payload: data.active_agents || [] });
        }
      } catch (e) {
        console.error('Failed to poll terminals/agents', e);
      }
    };

    poll();

    const hasRunningTerminals = (state.terminals || []).some(t => t.status === 'running');
    const speed = (state.isStreaming || hasRunningTerminals) ? 500 : 1500;

    intervalId = setInterval(poll, speed);
    return () => clearInterval(intervalId);
  }, [state.isStreaming, state.terminals?.length, dispatch]);

  function executeNewChat() {
    const currentMessages = state.messages['single_session'] || [];
    if (currentMessages.length === 0) return;

    // 1. Fetch existing archive
    let archive = [];
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('devops_concierge_archived_sessions');
      if (saved) {
        try {
          archive = JSON.parse(saved);
        } catch (e) {}
      }
    }

    // 2. Generate a title
    const firstUserMsg = currentMessages.find(m => m.role === 'user');
    const title = firstUserMsg 
      ? (firstUserMsg.content.slice(0, 45) + (firstUserMsg.content.length > 45 ? '...' : ''))
      : `Chat on ${new Date().toLocaleDateString()}`;

    // 3. Create archive entry
    const currentSessionArchive = {
      id: 'session_' + Date.now(),
      title,
      timestamp: new Date().toLocaleString(),
      messages: currentMessages
    };

    archive = [currentSessionArchive, ...archive];
    localStorage.setItem('devops_concierge_archived_sessions', JSON.stringify(archive));

    // Delete the session on the backend database to prevent history ghosting
    deleteSession('single_session').catch(err => console.error('Failed to clear backend session', err));

    // 4. Reset messages to start a new chat
    dispatch({
      type: 'SET_MESSAGES',
      sessionId: 'single_session',
      payload: []
    });
  }

  function executeClearConversation() {
    const currentMessages = state.messages['single_session'] || [];
    if (currentMessages.length === 0) return;

    // 1. Fetch existing archive
    let archive = [];
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('devops_concierge_archived_sessions');
      if (saved) {
        try {
          archive = JSON.parse(saved);
        } catch (e) {}
      }
    }

    // 2. Generate a meaningful title
    const firstUserMsg = currentMessages.find(m => m.role === 'user');
    const title = firstUserMsg 
      ? (firstUserMsg.content.slice(0, 45) + (firstUserMsg.content.length > 45 ? '...' : ''))
      : `Chat on ${new Date().toLocaleDateString()}`;

    // 3. Create archive entry
    const currentSessionArchive = {
      id: 'session_' + Date.now(),
      title,
      timestamp: new Date().toLocaleString(),
      messages: currentMessages
    };

    archive = [currentSessionArchive, ...archive];
    localStorage.setItem('devops_concierge_archived_sessions', JSON.stringify(archive));

    // Delete the session on the backend database to prevent history ghosting
    deleteSession('single_session').catch(err => console.error('Failed to clear backend session', err));

    // 4. Clear current messages in state
    dispatch({
      type: 'SET_MESSAGES',
      sessionId: 'single_session',
      payload: []
    });

    setConfirmClearOpen(false);
  }

  const currentMessages = state.messages['single_session'] || [];

  return (
    <div className="app-layout">
      <main className="chat-main">
        <header className="chat-header">
          <div className="chat-header-left" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <img 
              src="/logo.png" 
              alt="DevOps Concierge Logo" 
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                boxShadow: '0 0 10px rgba(6, 182, 212, 0.2)',
                objectFit: 'cover'
              }}
            />
            <span className="premium-header-title" style={{ fontFamily: '"Outfit", "Inter", sans-serif', fontWeight: '700', letterSpacing: '-0.5px' }}>
              DevOps Concierge Agent
            </span>
          </div>
          <div className="chat-header-right" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            
            {/* NEW CHAT BUTTON */}
            <button
              onClick={executeNewChat}
              style={{
                background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%)',
                border: '1px solid rgba(6, 182, 212, 0.4)',
                borderRadius: '8px',
                padding: '6px 12px',
                color: '#fff',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                boxShadow: '0 0 12px rgba(6, 182, 212, 0.25)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-1px) scale(1.03)';
                e.currentTarget.style.boxShadow = '0 0 18px rgba(6, 182, 212, 0.45)';
                e.currentTarget.style.borderColor = 'var(--accent-cyan)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                e.currentTarget.style.boxShadow = '0 0 12px rgba(6, 182, 212, 0.25)';
                e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.4)';
              }}
            >
              ➕ New Chat
            </button>

            {/* SEE HISTORY BUTTON */}
            <button
              onClick={() => dispatch({ type: 'TOGGLE_HISTORY' })}
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--border-glass)',
                borderRadius: '8px',
                padding: '6px 12px',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                e.currentTarget.style.color = '#fff';
                e.currentTarget.style.borderColor = 'var(--accent-cyan)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                e.currentTarget.style.color = 'var(--text-secondary)';
                e.currentTarget.style.borderColor = 'var(--border-glass)';
              }}
            >
              📜 History
            </button>

            {/* SEE TERMINAL BUTTON */}
            <button
              onClick={() => dispatch({ type: 'TOGGLE_TERMINAL' })}
              style={{
                background: (state.terminals || []).some(t => t.status === 'running')
                  ? 'linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%)'
                  : 'rgba(255, 255, 255, 0.04)',
                border: (state.terminals || []).some(t => t.status === 'running')
                  ? '1px solid var(--accent-cyan)'
                  : '1px solid var(--border-glass)',
                borderRadius: '8px',
                padding: '6px 12px',
                color: (state.terminals || []).some(t => t.status === 'running') ? '#fff' : 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                e.currentTarget.style.color = '#fff';
                e.currentTarget.style.borderColor = 'var(--accent-cyan)';
              }}
              onMouseLeave={e => {
                const isRunning = (state.terminals || []).some(t => t.status === 'running');
                e.currentTarget.style.background = isRunning
                  ? 'linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%)'
                  : 'rgba(255, 255, 255, 0.04)';
                e.currentTarget.style.color = isRunning ? '#fff' : 'var(--text-secondary)';
                e.currentTarget.style.borderColor = isRunning ? 'var(--accent-cyan)' : 'var(--border-glass)';
              }}
            >
              💻 Terminal {(state.terminals || []).filter(t => t.status === 'running').length > 0 && (
                <span className="header-terminal-badge">
                  {(state.terminals || []).filter(t => t.status === 'running').length}
                </span>
              )}
            </button>

            {/* CLEAR CONVERSATION BUTTON */}
            <button
              onClick={() => setConfirmClearOpen(true)}
              disabled={currentMessages.length === 0}
              style={{
                background: 'rgba(239, 68, 68, 0.03)',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                borderRadius: '8px',
                padding: '6px 12px',
                color: 'rgba(239, 68, 68, 0.85)',
                fontSize: '12px',
                fontWeight: '600',
                cursor: currentMessages.length === 0 ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease',
                opacity: currentMessages.length === 0 ? 0.4 : 1
              }}
              onMouseEnter={e => {
                if (currentMessages.length > 0) {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)';
                  e.currentTarget.style.color = 'var(--accent-red)';
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                }
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.03)';
                e.currentTarget.style.color = 'rgba(239, 68, 68, 0.85)';
                e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.2)';
              }}
            >
              🗑️ Clear Chat
            </button>


            {/* SETTINGS BUTTON */}
            <button
              className="settings-btn"
              onClick={() => dispatch({ type: 'TOGGLE_SETTINGS' })}
              style={{
                marginLeft: '4px'
              }}
            >
              ⚙️
            </button>
          </div>
        </header>

        <AgentStatusBar />
        <ChatArea />
        <InputBar />
      </main>

      <SettingsPanel />
      <HistoryPanel />
      <AuthorizationModal />
      <OnboardingModal />
      <TerminalPanel />

      {/* CUSTOM CONFIRM CLEAR CHAT MODAL */}
      <CustomConfirmModal
        isOpen={confirmClearOpen}
        title="Clear Current Conversation?"
        message="Are you sure you want to clear this active conversation? It will be safely archived in your history drawer so you can restore or view it anytime."
        confirmText="Clear & Archive"
        cancelText="Cancel"
        isDestructive={false}
        onConfirm={executeClearConversation}
        onCancel={() => setConfirmClearOpen(false)}
      />
    </div>
  );
}
