'use client';
import { useApp } from '../context/AppContext';

export default function AgentStatusBar() {
  const { state } = useApp();

  if (!state.activeAgents || state.activeAgents.length === 0) {
    if (!state.isStreaming) return null;
    return (
      <div className="agent-status-bar">
        <div className="agent-badge">
          <span className="dot" />
          <span>Primary Agent</span>
        </div>
      </div>
    );
  }

  return (
    <div className="agent-status-bar">
      {state.activeAgents.map((agent, i) => (
        <div key={i} className="agent-badge">
          <span className="dot" style={{ background: agent.status === 'done' ? 'var(--accent-green)' : 'var(--accent-amber)' }} />
          <span>{agent.name || `Agent ${i + 1}`}</span>
        </div>
      ))}
    </div>
  );
}
