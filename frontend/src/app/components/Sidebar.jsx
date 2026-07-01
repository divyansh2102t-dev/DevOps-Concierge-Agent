'use client';
import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { fetchSessions, deleteSession } from '../services/api';

export default function Sidebar() {
  const { state, dispatch } = useApp();
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      const sessions = await fetchSessions(search || undefined);
      dispatch({ type: 'SET_SESSIONS', payload: sessions });
    } catch {}
  }

  useEffect(() => {
    const timer = setTimeout(() => loadSessions(), 300);
    return () => clearTimeout(timer);
  }, [search]);

  function handleNewChat() {
    dispatch({ type: 'SET_CURRENT_SESSION', payload: null });
  }

  async function handleDelete(e, id) {
    e.stopPropagation();
    await deleteSession(id);
    if (state.currentSessionId === id) {
      dispatch({ type: 'SET_CURRENT_SESSION', payload: null });
    }
    loadSessions();
  }

  function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diff = now - d;
    if (diff < 86400000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff < 604800000) return d.toLocaleDateString([], { weekday: 'short' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  return (
    <aside className={`sidebar ${state.sidebarOpen ? '' : 'collapsed'}`}>
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">🚀</div>
          <div className="sidebar-brand-text">
            <h2>DevOps Concierge</h2>
            <span>v1.0 • AI Agent</span>
          </div>
        </div>
        <button className="new-chat-btn" onClick={handleNewChat}>
          <span>+</span> New Chat
        </button>
      </div>

      <div className="sidebar-search">
        <input
          type="text"
          placeholder="Search conversations..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          autoComplete="off"
          name="concierge-search"
        />
      </div>

      <div className="conversation-list">
        {state.sessions.map(s => (
          <div
            key={s.id}
            className={`conversation-item ${state.currentSessionId === s.id ? 'active' : ''}`}
            onClick={() => dispatch({ type: 'SET_CURRENT_SESSION', payload: s.id })}
          >
            <span className="title">{s.title}</span>
            <span className="time">{formatTime(s.updated_at)}</span>
            <button className="delete-btn" onClick={e => handleDelete(e, s.id)}>✕</button>
          </div>
        ))}
      </div>
    </aside>
  );
}
