'use client';
import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import CustomConfirmModal from './CustomConfirmModal';

export default function HistoryPanel() {
  const { state, dispatch } = useApp();
  const [archivedSessions, setArchivedSessions] = useState([]);
  const [confirmDeleteAllOpen, setConfirmDeleteAllOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState(null);

  // Load archived sessions when the history panel opens
  useEffect(() => {
    if (state.historyOpen) {
      loadArchivedSessions();
    }
  }, [state.historyOpen]);

  function loadArchivedSessions() {
    if (typeof window === 'undefined') return;
    const saved = localStorage.getItem('devops_concierge_archived_sessions');
    if (saved) {
      try {
        setArchivedSessions(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to load archived sessions', e);
      }
    } else {
      setArchivedSessions([]);
    }
  }

  function handleClose() {
    dispatch({ type: 'CLOSE_HISTORY' });
  }

  // Restores an archived session, swapping it with the current active chat if needed
  function handleRestoreSession(session) {
    if (typeof window === 'undefined') return;
    
    const currentMessages = state.messages['single_session'] || [];
    let updatedArchive = [...archivedSessions].filter(s => s.id !== session.id);

    // If the current active chat is not empty, archive it first so work is never lost!
    if (currentMessages.length > 0) {
      const firstUserMsg = currentMessages.find(m => m.role === 'user');
      const title = firstUserMsg 
        ? (firstUserMsg.content.slice(0, 45) + (firstUserMsg.content.length > 45 ? '...' : ''))
        : `Chat on ${new Date().toLocaleDateString()}`;

      const currentSessionArchive = {
        id: 'session_' + Date.now(),
        title,
        timestamp: new Date().toLocaleString(),
        messages: currentMessages
      };
      updatedArchive = [currentSessionArchive, ...updatedArchive];
    }

    // Save the new archive list
    localStorage.setItem('devops_concierge_archived_sessions', JSON.stringify(updatedArchive));
    setArchivedSessions(updatedArchive);

    // Load the restored messages into the active chat
    dispatch({
      type: 'SET_MESSAGES',
      sessionId: 'single_session',
      payload: session.messages
    });

    // Close history panel and refresh view
    dispatch({ type: 'CLOSE_HISTORY' });
  }

  // Triggers deletion flow for a specific session
  function handleDeleteSessionClick(session, e) {
    e.stopPropagation(); // Avoid triggering restore on click
    setSessionToDelete(session);
  }

  // Executes actual deletion of the session
  function executeDeleteSession() {
    if (!sessionToDelete) return;
    const updated = archivedSessions.filter(s => s.id !== sessionToDelete.id);
    localStorage.setItem('devops_concierge_archived_sessions', JSON.stringify(updated));
    setArchivedSessions(updated);
    setSessionToDelete(null);
  }

  // Executes actual clear of all history
  function executeClearAllHistory() {
    localStorage.removeItem('devops_concierge_archived_sessions');
    setArchivedSessions([]);
    setConfirmDeleteAllOpen(false);
  }

  if (!state.historyOpen) return null;

  return (
    <>
      <div className="settings-overlay" onClick={handleClose} style={{ zIndex: 990 }} />
      <div className="settings-panel history-panel" style={{
        left: 0,
        right: 'auto',
        borderLeft: 'none',
        borderRight: '1px solid var(--border-glass)',
        transform: 'translateX(0)',
        zIndex: 995,
        background: 'linear-gradient(135deg, rgba(13, 17, 23, 0.95) 0%, rgba(20, 26, 35, 0.95) 100%)',
      }}>
        
        {/* HEADER */}
        <div className="settings-header" style={{
          borderBottom: '1px solid var(--border-glass)',
          paddingBottom: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '20px' }}>📜</span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '800' }}>Conversation History</h3>
          </div>
          <button className="settings-close" onClick={handleClose}>✕</button>
        </div>

        {/* BODY / LIST */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 0',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {archivedSessions.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '200px',
              color: 'var(--text-muted)',
              textAlign: 'center',
              padding: '0 20px'
            }}>
              <span style={{ fontSize: '32px', marginBottom: '12px', opacity: 0.5 }}>📂</span>
              <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5' }}>
                Your history is empty.<br />
                Archived chats will appear here when you clear them from your screen.
              </p>
            </div>
          ) : (
            archivedSessions.map(session => (
              <div
                key={session.id}
                onClick={() => handleRestoreSession(session)}
                className="key-card"
                style={{
                  cursor: 'pointer',
                  background: 'rgba(255, 255, 255, 0.02)',
                  transition: 'all 0.2s ease',
                  border: '1px solid var(--border-glass)',
                  position: 'relative',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                  e.currentTarget.style.borderColor = 'var(--accent-cyan)';
                  e.currentTarget.style.boxShadow = '0 0 12px rgba(6, 182, 212, 0.15)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                  e.currentTarget.style.borderColor = 'var(--border-glass)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <span style={{
                    fontSize: '13px',
                    fontWeight: '600',
                    color: '#fff',
                    paddingRight: '28px',
                    lineHeight: '1.4',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical'
                  }}>
                    {session.title}
                  </span>
                  <button
                    onClick={(e) => handleDeleteSessionClick(session, e)}
                    className="settings-close"
                    style={{
                      position: 'absolute',
                      top: '10px',
                      right: '10px',
                      padding: '4px',
                      fontSize: '11px',
                      color: 'var(--text-muted)',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer'
                    }}
                    onMouseEnter={e => e.target.style.color = 'var(--accent-red)'}
                    onMouseLeave={e => e.target.style.color = 'var(--text-muted)'}
                  >
                    ✕
                  </button>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '10px',
                  color: 'var(--text-muted)',
                  marginTop: '4px'
                }}>
                  <span>📅 {session.timestamp.split(',')[0]}</span>
                  <span style={{
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid var(--border-glass)',
                    fontWeight: '600'
                  }}>
                    💬 {session.messages.length} messages
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* FOOTER */}
        {archivedSessions.length > 0 && (
          <div style={{
            borderTop: '1px solid var(--border-glass)',
            paddingTop: '16px',
            display: 'flex',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <button
              onClick={() => setConfirmDeleteAllOpen(true)}
              style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: '6px',
                color: 'var(--accent-red)',
                fontSize: '11px',
                fontWeight: '600',
                padding: '8px 16px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                width: '100%'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)';
                e.currentTarget.style.boxShadow = '0 0 10px rgba(239, 68, 68, 0.1)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              🗑️ Clear All Conversation History
            </button>
          </div>
        )}

      </div>

      {/* CUSTOM CONFIRMATION MODALS */}
      <CustomConfirmModal
        isOpen={confirmDeleteAllOpen}
        title="Clear Conversation History?"
        message="Are you sure you want to permanently delete ALL archived conversation history? This action is destructive and cannot be undone."
        confirmText="🗑️ Delete All"
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={executeClearAllHistory}
        onCancel={() => setConfirmDeleteAllOpen(false)}
      />

      <CustomConfirmModal
        isOpen={!!sessionToDelete}
        title="Delete Conversation?"
        message={sessionToDelete ? `Are you sure you want to delete "${sessionToDelete.title}" from your archives?` : ''}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={executeDeleteSession}
        onCancel={() => setSessionToDelete(null)}
      />
    </>
  );
}
