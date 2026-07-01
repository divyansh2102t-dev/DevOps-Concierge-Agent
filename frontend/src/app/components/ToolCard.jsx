'use client';
import { useState } from 'react';

const TOOL_ICONS = {
  parse_url: '🌐',
  scaffold_project: '🏗️',
  select_database: '🗄️',
  generate_db_config: '⚙️',
  extract_credentials: '🔑',
  generate_env_file: '📄',
  create_github_repo: '🐙',
  push_to_github: '📤',
  deploy_to_vercel: '🚀',
  set_vercel_env: '🔧',
  generate_docs: '📊',
  connect_mcp_server: '🔌',
  run_terminal_command: '💻',
  read_project_file: '📖',
  write_project_file: '✏️',
};

export default function ToolCard({ data }) {
  const [expanded, setExpanded] = useState(false);
  const icon = TOOL_ICONS[data.toolName] || '⚡';
  const statusClass = data.status || 'running';

  return (
    <div className={`tool-card ${expanded ? 'is-expanded' : ''}`} onClick={() => setExpanded(!expanded)}>
      <div className="tool-card-header">
        <div className={`tool-icon ${statusClass}`}>
          {statusClass === 'running' ? '⏳' : statusClass === 'success' ? '✅' : statusClass === 'error' ? '❌' : icon}
        </div>
        <span className="tool-card-name">{icon} {formatToolName(data.toolName)}</span>
        <span className="tool-card-status">
          {statusClass}
          <span className="expand-indicator">{expanded ? ' ▴' : ' ▾'}</span>
        </span>
      </div>

      {expanded && (
        <div className="tool-card-expanded-body" onClick={(e) => e.stopPropagation()}>
          {/* Section 1: Inputs / Arguments */}
          {data.arguments && Object.keys(data.arguments).length > 0 && (
            <div className="tool-expanded-section">
              <div className="tool-section-label">Parameters & Arguments</div>
              {renderArguments(data.toolName, data.arguments)}
            </div>
          )}

          {/* Section 2: Outputs / Progress */}
          <div className="tool-expanded-section">
            <div className="tool-section-label">Execution Output</div>
            {statusClass === 'running' && (
              <div className="tool-active-running">
                <span className="tool-pulse-dot"></span>
                <span className="tool-running-text">Executing tool locally on your machine...</span>
              </div>
            )}

            {statusClass === 'success' && data.result && (
              <div className="tool-output-success">
                {renderResult(data.toolName, data.result)}
              </div>
            )}

            {statusClass === 'error' && (
              <div className="tool-output-error-container">
                <div className="tool-error-title">❌ Error executing tool:</div>
                <pre className="tool-error-pre">
                  {data.result?.error || data.result?.message || (typeof data.result === 'string' ? data.result : JSON.stringify(data.result || 'Unknown error occurred', null, 2))}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SELF-CONTAINED PREMIUM STYLING */}
      <style>{`
        .tool-card {
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          border-color: rgba(255, 255, 255, 0.08);
          position: relative;
          overflow: hidden;
          background: rgba(19, 24, 41, 0.5) !important;
          flex-shrink: 0; /* Prevent squishing in flexbox containers */
        }
        .tool-card:hover {
          border-color: rgba(6, 182, 212, 0.35);
          box-shadow: 0 4px 20px rgba(6, 182, 212, 0.08);
          transform: translateY(-1px);
        }
        .tool-card.is-expanded {
          border-color: rgba(139, 92, 246, 0.3);
          box-shadow: 0 4px 25px rgba(139, 92, 246, 0.08);
          background: rgba(19, 24, 41, 0.8) !important;
        }
        .tool-card-header {
          cursor: pointer;
          user-select: none;
        }
        .expand-indicator {
          font-size: 12px;
          opacity: 0.7;
          margin-left: 6px;
        }
        .tool-card-expanded-body {
          margin-top: 14px;
          padding-top: 14px;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
          display: flex;
          flex-direction: column;
          gap: 16px;
          animation: slideDownFade 0.2s ease-out;
        }
        @keyframes slideDownFade {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .tool-expanded-section {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .tool-section-label {
          font-size: 11px;
          font-weight: 600;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        
        /* Parameters Styling */
        .tool-params-grid {
          display: flex;
          flex-direction: column;
          gap: 6px;
          background: rgba(0, 0, 0, 0.2);
          padding: 10px 12px;
          border-radius: 8px;
          border: 1px solid rgba(255, 255, 255, 0.04);
        }
        .tool-param-row {
          display: flex;
          font-size: 12px;
          line-height: 1.5;
        }
        .tool-param-label {
          font-weight: 500;
          color: var(--text-secondary);
          width: 130px;
          min-width: 130px;
        }
        .tool-param-value {
          font-family: 'JetBrains Mono', 'Fira Code', monospace;
          color: var(--accent-cyan);
          word-break: break-all;
        }
        
        /* Terminal / Pre Block Styling */
        .tool-terminal-pre {
          background: #060913 !important;
          border: 1px solid rgba(255, 255, 255, 0.05) !important;
          border-radius: 8px !important;
          padding: 12px 16px !important;
          margin: 6px 0 0 0 !important;
          max-height: 250px;
          overflow-y: auto;
          box-shadow: inset 0 2px 8px rgba(0,0,0,0.8);
          position: relative;
        }
        .tool-terminal-pre code {
          font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
          font-size: 12px !important;
          line-height: 1.6 !important;
          color: #38bdf8 !important; /* Sky blue console color */
          white-space: pre-wrap !important;
          word-break: break-all !important;
        }
        .tool-terminal-cmd {
          color: #34d399 !important; /* Mint green for input command */
          font-weight: 600;
        }
        
        /* Running Indicator */
        .tool-active-running {
          display: flex;
          align-items: center;
          gap: 8px;
          background: rgba(245, 158, 11, 0.03);
          border: 1px solid rgba(245, 158, 11, 0.1);
          padding: 10px 14px;
          border-radius: 8px;
        }
        .tool-pulse-dot {
          width: 8px;
          height: 8px;
          background: var(--accent-amber);
          border-radius: 50%;
          animation: toolBlink 1.4s ease-in-out infinite;
          box-shadow: 0 0 8px var(--accent-amber);
        }
        @keyframes toolBlink {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.3; transform: scale(0.9); }
        }
        .tool-running-text {
          font-size: 12px;
          color: var(--text-secondary);
        }
        
        /* Error Alert Styling */
        .tool-output-error-container {
          background: rgba(239, 68, 68, 0.03);
          border: 1px solid rgba(239, 68, 68, 0.15);
          border-radius: 8px;
          padding: 12px;
        }
        .tool-error-title {
          font-size: 12px;
          font-weight: 600;
          color: var(--accent-red);
          margin-bottom: 6px;
        }
        .tool-error-pre {
          background: transparent !important;
          padding: 0 !important;
          margin: 0 !important;
          border: none !important;
          font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
          font-size: 11.5px !important;
          color: #fca5a5 !important;
          white-space: pre-wrap !important;
          overflow: visible !important;
        }
      `}</style>
    </div>
  );
}

function formatToolName(name) {
  return (name || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function renderArguments(toolName, args) {
  if (toolName === 'run_terminal_command') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div className="tool-params-grid">
          <div className="tool-param-row">
            <span className="tool-param-label">📂 Working Dir:</span>
            <span className="tool-param-value">{args.working_dir || './'}</span>
          </div>
          <div className="tool-param-row">
            <span className="tool-param-label">⚙️ Background:</span>
            <span className="tool-param-value">{args.run_in_background ? 'Yes (Non-blocking)' : 'No (Blocking)'}</span>
          </div>
        </div>
        <pre className="tool-terminal-pre">
          <code>
            <span className="tool-terminal-cmd">$ {args.command}</span>
          </code>
        </pre>
      </div>
    );
  }

  if (toolName === 'write_project_file' || toolName === 'read_project_file') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div className="tool-params-grid">
          <div className="tool-param-row">
            <span className="tool-param-label">📄 File Path:</span>
            <span className="tool-param-value">{args.file_path}</span>
          </div>
        </div>
        {args.content && (
          <pre className="tool-terminal-pre">
            <code style={{ color: '#e2e8f0' }}>{args.content}</code>
          </pre>
        )}
      </div>
    );
  }

  // General parameters
  return (
    <div className="tool-params-grid">
      {Object.entries(args).map(([key, val]) => (
        <div className="tool-param-row" key={key}>
          <span className="tool-param-label">🔹 {key.replace(/_/g, ' ')}:</span>
          <span className="tool-param-value">
            {typeof val === 'object' ? JSON.stringify(val) : String(val)}
          </span>
        </div>
      ))}
    </div>
  );
}

function renderResult(toolName, result) {
  const consoleOutput = result.output || result.stdout || result.message || (typeof result === 'string' ? result : null);
  const errorOutput = result.stderr;

  if (consoleOutput || errorOutput) {
    return (
      <pre className="tool-terminal-pre">
        <code>
          {consoleOutput}
          {errorOutput && (
            <span style={{ color: '#f87171', display: 'block', marginTop: '8px' }}>
              {errorOutput}
            </span>
          )}
        </code>
      </pre>
    );
  }

  return (
    <pre className="tool-terminal-pre">
      <code style={{ color: '#a5b4fc' }}>{JSON.stringify(result, null, 2)}</code>
    </pre>
  );
}
