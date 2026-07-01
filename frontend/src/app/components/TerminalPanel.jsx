'use client';
import { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { API_BASE } from '../services/api';

export default function TerminalPanel() {
  const { state, dispatch } = useApp();
  const [selectedCommandId, setSelectedCommandId] = useState(null);
  const [killing, setKilling] = useState(null); // cmd_id being killed
  const outputRef = useRef(null);

  const terminals = state.terminals || [];
  const activeSelectedId = selectedCommandId || (terminals.length > 0 ? terminals[0].command_id : null);
  const selectedTerminal = terminals.find(t => t.command_id === activeSelectedId);

  // Auto-scroll terminal output to bottom when selected terminal's output changes
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [selectedTerminal?.stdout, selectedTerminal?.stderr]);

  // Handler to clear terminal logs on backend
  const handleClearLogs = async () => {
    try {
      await fetch(`${API_BASE}/api/chat/terminals/clear`, { method: 'POST' });
      dispatch({ type: 'SET_TERMINALS', payload: [] });
      setSelectedCommandId(null);
    } catch (e) {
      console.error('Failed to clear terminals', e);
    }
  };

  // Handler to kill a specific running process
  const handleKill = async (e, cmdId) => {
    e.stopPropagation(); // don't also select this item
    setKilling(cmdId);
    try {
      await fetch(`${API_BASE}/api/chat/terminals/${cmdId}/kill`, { method: 'POST' });
    } catch (err) {
      console.error('Failed to kill process', err);
    } finally {
      setKilling(null);
    }
  };

  // If panel is closed, do not render (must be placed AFTER all hooks to prevent React hook order violation)
  if (!state.terminalOpen) return null;

  const activeCount = terminals.filter(t => t.status === 'running').length;

  return (
    <div className="terminal-panel-overlay">
      <div className="terminal-panel-container">
        {/* HEADER */}
        <header className="terminal-panel-header">
          <div className="terminal-header-left">
            <span className="terminal-icon">💻</span>
            <h3 className="terminal-title">Active Terminal Shells</h3>
            {activeCount > 0 && (
              <span className="terminal-badge-pulse">
                {activeCount} active
              </span>
            )}
          </div>
          <div className="terminal-header-right">
            {terminals.length > 0 && (
              <button className="terminal-clear-btn" onClick={handleClearLogs}>
                🗑️ Clear Logs
              </button>
            )}
            <button className="terminal-close-btn" onClick={() => dispatch({ type: 'TOGGLE_TERMINAL' })}>
              ✕
            </button>
          </div>
        </header>

        {/* BODY */}
        <div className="terminal-panel-body">
          {terminals.length === 0 ? (
            <div className="terminal-empty-state">
              <span className="empty-icon">📂</span>
              <p className="empty-text">No command executions recorded in this session yet.</p>
              <p className="empty-subtext">Commands run by the agent will stream their live outputs here in real-time.</p>
            </div>
          ) : (
            <>
              {/* SIDEBAR - COMMANDS LIST */}
              <div className="terminal-sidebar">
                {terminals.map((t) => {
                  const isActive = t.command_id === selectedTerminal?.command_id;
                  const isRunning = t.status === 'running';
                  const isError = t.status === 'error';
                  const isBeingKilled = killing === t.command_id;
                  
                  return (
                    <button
                      key={t.command_id}
                      className={`terminal-sidebar-item ${isActive ? 'active' : ''}`}
                      onClick={() => setSelectedCommandId(t.command_id)}
                    >
                      <div className="item-status-indicator">
                        {isRunning ? (
                          <span className="status-dot running" />
                        ) : isError ? (
                          <span className="status-dot error" />
                        ) : (
                          <span className="status-dot success" />
                        )}
                      </div>
                      <div className="item-details">
                        <div className="item-cmd-text" title={t.command}>{t.command}</div>
                        <div className="item-meta">
                          {t.pid && <span className="item-pid">PID: {t.pid}</span>}
                          <span className="item-duration">{t.duration}s</span>
                        </div>
                      </div>
                      {/* Per-process stop button — only visible on running processes */}
                      {isRunning && (
                        <button
                          className={`terminal-kill-btn ${isBeingKilled ? 'killing' : ''}`}
                          onClick={(e) => handleKill(e, t.command_id)}
                          title="Stop this process"
                          disabled={isBeingKilled}
                        >
                          {isBeingKilled ? '…' : '⏹'}
                        </button>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* OUTPUT DISPLAY */}
              <div className="terminal-output-container">
                {selectedTerminal ? (
                  <>
                    <div className="terminal-output-header">
                      <div className="output-header-left">
                        <span className="output-cwd-label">Directory:</span>
                        <span className="output-cwd-path">{selectedTerminal.working_dir}</span>
                      </div>
                      <div className="output-header-right">
                        <span className={`output-status-pill ${selectedTerminal.status}`}>
                          {selectedTerminal.status.toUpperCase()}
                        </span>
                        {/* Stop button in the output header for the selected process */}
                        {selectedTerminal.killable && (
                          <button
                            className={`terminal-kill-btn header-kill ${killing === selectedTerminal.command_id ? 'killing' : ''}`}
                            onClick={(e) => handleKill(e, selectedTerminal.command_id)}
                            title="Stop this process"
                            disabled={killing === selectedTerminal.command_id}
                          >
                            {killing === selectedTerminal.command_id ? '…' : '⏹ Stop'}
                          </button>
                        )}
                      </div>
                    </div>
                    <pre ref={outputRef} className="terminal-output-pre">
                      {selectedTerminal.stdout || selectedTerminal.stderr ? (
                        <>
                          {selectedTerminal.stdout && <span className="stdout-text">{selectedTerminal.stdout}</span>}
                          {selectedTerminal.stderr && <span className="stderr-text">{selectedTerminal.stderr}</span>}
                        </>
                      ) : (
                        <span className="terminal-waiting-text">Initializing terminal stream...</span>
                      )}
                    </pre>
                  </>
                ) : (
                  <div className="terminal-output-empty">
                    <p>Select a command from the list to view its terminal output.</p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
