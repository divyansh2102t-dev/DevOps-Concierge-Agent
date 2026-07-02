'use client';
import { useState, useEffect } from 'react';

function parseMessageContent(content, isStreaming) {
  if (!content) return { thinking: '', response: '', isThinking: false };

  const thinkStartTag = '<think>';
  const thinkEndTag = '</think>';

  const thinkStartIdx = content.indexOf(thinkStartTag);
  if (thinkStartIdx !== -1) {
    const thinkEndIdx = content.indexOf(thinkEndTag);
    if (thinkEndIdx !== -1) {
      // Both start and end tags are present
      const thinking = content.slice(thinkStartIdx + thinkStartTag.length, thinkEndIdx).trim();
      const response = content.slice(thinkEndIdx + thinkEndTag.length).trim();
      
      // If the model put everything inside <think> and wrote nothing outside,
      // treat the thinking content as the actual response.
      if (!response && thinking) {
        return { thinking: '', response: thinking, isThinking: false };
      }
      return { thinking, response, isThinking: false };
    } else {
      // Only start tag is present, no end tag
      if (isStreaming) {
        // Still streaming: actively thinking
        const thinking = content.slice(thinkStartIdx + thinkStartTag.length).trim();
        return { thinking, response: '', isThinking: true };
      } else {
        // Stream finished, but no closing </think> tag!
        // Treat the entire content after the start tag as the response to avoid hiding it.
        const response = content.slice(thinkStartIdx + thinkStartTag.length).trim();
        return { thinking: '', response, isThinking: false };
      }
    }
  }

  return { thinking: '', response: content, isThinking: false };
}

export default function MessageBubble({ message, isLast, onRetry, isStreaming }) {
  const isUser = message.role === 'user';
  const { thinking, response, isThinking } = isUser 
    ? { thinking: '', response: message.content, isThinking: false }
    : parseMessageContent(message.content, isStreaming);

  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);
  const [seconds, setSeconds] = useState(0);
  const [hasCollapsed, setHasCollapsed] = useState(false);
  const [showWarningDetails, setShowWarningDetails] = useState(false);
  const [warningIgnored, setWarningIgnored] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // High-precision decimal timer for active thinking
  useEffect(() => {
    let interval;
    if (isThinking) {
      const startTime = Date.now();
      interval = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        setSeconds(elapsed);
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isThinking]);

  // Auto-collapse when thinking completes
  useEffect(() => {
    if (!isThinking && seconds > 0 && !hasCollapsed) {
      setIsExpanded(false);
      setHasCollapsed(true);
    }
  }, [isThinking, seconds, hasCollapsed]);

  // Collapse historical chats by default
  useEffect(() => {
    if (!isThinking && seconds === 0) {
      setIsExpanded(false);
    }
  }, [isThinking, seconds]);

  if (warningIgnored) return null;

  if (message.content && message.content.includes('No Active AI Engine Available!')) {
    return (
      <div className="message assistant" style={{ marginBottom: '16px' }}>
        <div className="message-content" style={{
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          borderRadius: '8px',
          padding: '14px',
          color: '#fff'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: '700', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              ⚠️ No Active AI Engine Available!
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setShowWarningDetails(!showWarningDetails)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid var(--border-glass)',
                  borderRadius: '4px',
                  color: 'var(--accent-cyan)',
                  padding: '4px 8px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                {showWarningDetails ? '▲ Hide Details' : '▼ Show Options'}
              </button>
              <button
                onClick={() => setWarningIgnored(true)}
                style={{
                  background: 'rgba(239, 68, 68, 0.25)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  borderRadius: '4px',
                  color: '#fff',
                  padding: '4px 8px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                ✕ Ignore
              </button>
            </div>
          </div>

          {showWarningDetails && (
            <div style={{ 
              marginTop: '12px', 
              paddingTop: '12px', 
              borderTop: '1px solid rgba(239, 68, 68, 0.2)',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              lineHeight: '1.6'
            }}>
              <p style={{ margin: '0 0 8px 0' }}>To start chatting, please choose one of these options:</p>
              <ul style={{ paddingLeft: '18px', margin: 0 }}>
                <li style={{ marginBottom: '6px' }}>
                  <strong>Option A (Cloud):</strong> Get a free <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-cyan)' }}>Gemini API Key here ↗</a>, then add it in the <strong>Settings panel</strong> (click the gear icon ⚙️ in the top-right corner of this page).
                </li>
                <li>
                  <strong>Option B (Offline):</strong> Download the <a href="https://ollama.com/download" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-cyan)' }}>Ollama App here ↗</a> and run it. Once running, open the <strong>Settings panel</strong> (gear icon ⚙️) and click <strong>Install</strong> on the <strong>Qwen 2.5 Coder 1.5B</strong> model to run completely offline and free!
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  }
  const imageUrls = message.tool_data?.images || [];

  function handleCopy() {
    navigator.clipboard.writeText(message.content || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function renderContent(content) {
    if (!content) return null;

    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, i) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const lines = part.slice(3, -3);
        const firstNewline = lines.indexOf('\n');
        const lang = firstNewline > 0 ? lines.slice(0, firstNewline).trim() : '';
        const code = firstNewline > 0 ? lines.slice(firstNewline + 1) : lines;
        return <CodeBlock key={i} code={code} lang={lang} />;
      }

      return <span key={i} dangerouslySetInnerHTML={{ __html: formatMarkdown(part) }} />;
    });
  }

  function escapeHTML(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;');
  }

  function formatInline(text) {
    return escapeHTML(text)
      .replace(/\\Delta/g, 'Δ')
      .replace(/\\alpha/g, 'α')
      .replace(/\\beta/g, 'β')
      .replace(/\\theta/g, 'θ')
      .replace(/\\pi/g, 'π')
      .replace(/\\\((.*?)\\\)/g, '$1')
      .replace(/\\\[([\s\S]*?)\\\]/g, '$1')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  function formatMarkdown(text) {
    const lines = text.split('\n');
    const output = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // --- Table detection: look for a pipe-separated row followed by a separator row ---
      if (/^\|.+\|/.test(line) && i + 1 < lines.length && /^\|[\s\-|:]+\|/.test(lines[i + 1])) {
        const headers = line.split('|').slice(1, -1).map(h => h.trim());
        i += 2; // skip header + separator
        const rows = [];
        while (i < lines.length && /^\|.+\|/.test(lines[i])) {
          rows.push(lines[i].split('|').slice(1, -1).map(c => c.trim()));
          i++;
        }
        const headerHtml = headers.map(h => `<th>${formatInline(h)}</th>`).join('');
        const rowsHtml = rows.map(r =>
          `<tr>${r.map(c => {
            const lower = c.toLowerCase();
            const isConfigured = lower === 'configured' || lower === 'true' || lower === '✓' || lower === 'yes';
            const isMissing = lower === 'missing' || lower === 'false' || lower === '✗' || lower === 'no';
            const badge = isConfigured
              ? `<span style="color:#4ade80;font-weight:600;">✓ Configured</span>`
              : isMissing
              ? `<span style="color:#f87171;font-weight:600;">✗ Missing</span>`
              : formatInline(c);
            return `<td>${badge}</td>`;
          }).join('')}</tr>`
        ).join('');
        output.push(`<div class="md-table-wrap"><table class="md-table"><thead><tr>${headerHtml}</tr></thead><tbody>${rowsHtml}</tbody></table></div>`);
        continue;
      }

      // --- Headings ---
      const h3 = line.match(/^###\s+(.*)/);
      const h2 = line.match(/^##\s+(.*)/);
      const h1 = line.match(/^#\s+(.*)/);
      if (h3) { output.push(`<h3 class="md-h3">${formatInline(h3[1])}</h3>`); i++; continue; }
      if (h2) { output.push(`<h2 class="md-h2">${formatInline(h2[1])}</h2>`); i++; continue; }
      if (h1) { output.push(`<h1 class="md-h1">${formatInline(h1[1])}</h1>`); i++; continue; }

      // --- Horizontal rule ---
      if (/^---+$/.test(line.trim())) { output.push('<hr class="md-hr"/>'); i++; continue; }

      // --- Bullet list ---
      if (/^[-*]\s+/.test(line)) {
        const items = [];
        while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
          items.push(`<li>${formatInline(lines[i].replace(/^[-*]\s+/, ''))}</li>`);
          i++;
        }
        output.push(`<ul class="md-ul">${items.join('')}</ul>`);
        continue;
      }

      // --- Numbered list ---
      if (/^\d+\.\s+/.test(line)) {
        const items = [];
        while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
          items.push(`<li>${formatInline(lines[i].replace(/^\d+\.\s+/, ''))}</li>`);
          i++;
        }
        output.push(`<ol class="md-ol">${items.join('')}</ol>`);
        continue;
      }

      // --- Empty line → paragraph break ---
      if (line.trim() === '') { output.push('<br/>'); i++; continue; }

      // --- Regular text ---
      output.push(`<span>${formatInline(line)}</span><br/>`);
      i++;
    }

    return output.join('');
  }

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-content">
        {imageUrls.length > 0 && (
          <div 
            className="message-images-grid"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px',
              marginBottom: '12px'
            }}
          >
            {imageUrls.map((url, idx) => (
              <img
                key={idx}
                src={url.startsWith('data:') || url.startsWith('http') ? url : `${API_BASE}${url}`}
                alt={`Attached upload ${idx + 1}`}
                style={{
                  maxWidth: '240px',
                  maxHeight: '180px',
                  borderRadius: '8px',
                  objectFit: 'cover',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
                  cursor: 'zoom-in'
                }}
                onClick={(e) => {
                  window.open(e.currentTarget.src, '_blank');
                }}
              />
            ))}
          </div>
        )}
        {thinking && (
          <div className={`thinking-block ${isThinking ? 'thinking' : 'done'}`}>
            <div className="thinking-header" onClick={() => setIsExpanded(!isExpanded)}>
              <div className="thinking-header-left">
                {isThinking ? (
                  <span className="thinking-icon spinning">🧠</span>
                ) : (
                  <span className="thinking-icon success">✓</span>
                )}
                <span className="thinking-title">
                  {isThinking 
                    ? `Thinking... (${seconds.toFixed(1)}s)` 
                    : seconds > 0 
                      ? `Thought for ${seconds.toFixed(1)}s` 
                      : 'Thought process'
                  }
                </span>
              </div>
              <span className={`thinking-chevron ${isExpanded ? 'expanded' : ''}`}>▾</span>
            </div>
            {isExpanded && (
              <div className="thinking-body">
                {renderContent(thinking)}
              </div>
            )}
          </div>
        )}
        {renderContent(response)}
      </div>
      <div className={`message-actions ${isUser ? 'user-actions' : 'assistant-actions'}`}>
        <button
          className="msg-action-btn"
          onClick={handleCopy}
          title="Copy message"
        >
          {copied ? '✓ Copied' : '📋 Copy'}
        </button>
        {!isUser && isLast && !isStreaming && onRetry && (
          <button
            className="msg-action-btn retry-btn"
            onClick={onRetry}
            title="Regenerate response"
          >
            🔄 Retry
          </button>
        )}
      </div>
    </div>
  );
}

function CodeBlock({ code, lang }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <pre>
      <button className="copy-btn" onClick={handleCopy}>
        {copied ? '✓ Copied' : '📋 Copy'}
      </button>
      <code>{code}</code>
    </pre>
  );
}
