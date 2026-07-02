'use client';
import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { fetchKeys, saveKey, removeKey, addQueueKey, removeQueueKey, toggleKey, toggleQueueKey } from '../services/api';

export default function SettingsPanel() {
  const { state, dispatch } = useApp();
  const [keys, setKeys] = useState({});
  const [keyInputs, setKeyInputs] = useState({});
  const [queueKeys, setQueueKeys] = useState([]);
  const [highlightedField, setHighlightedField] = useState(null);

  const [isMobileDevice, setIsMobileDevice] = useState(() => {
    if (typeof window !== 'undefined') {
      const ua = window.navigator.userAgent.toLowerCase();
      return /android|iphone|ipad|ipod|windows phone/i.test(ua);
    }
    return false;
  });

  useEffect(() => {
    const handleHighlight = (e) => {
      const field = e.detail?.field;
      if (field) {
        setHighlightedField(field);
        setTimeout(() => {
          const el = document.getElementById(`key-card-${field}`);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 150);
        // Clear highlight after 6 seconds
        setTimeout(() => {
          setHighlightedField(null);
        }, 6000);
      }
    };
    window.addEventListener('highlight-setting-field', handleHighlight);
    return () => window.removeEventListener('highlight-setting-field', handleHighlight);
  }, []);

  // Add to Queue form state
  const [provider, setProvider] = useState('gemini');
  const [label, setLabel] = useState('');
  const [value, setValue] = useState('');
  const [addingToQueue, setAddingToQueue] = useState(false);

  // Ollama local integration state
  const [ollamaConnected, setOllamaConnected] = useState(false);
  const [localModels, setLocalModels] = useState([]);
  const [pullingModel, setPullingModel] = useState(null);
  const [pullProgress, setPullProgress] = useState(0);
  const [pullStatus, setPullStatus] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('devops_concierge_ollama_url') || 'http://localhost:11434';
    }
    return 'http://localhost:11434';
  });

  const handleOllamaUrlChange = (newUrl) => {
    setOllamaUrl(newUrl);
    if (typeof window !== 'undefined') {
      localStorage.setItem('devops_concierge_ollama_url', newUrl);
    }
  };

  useEffect(() => {
    checkOllama();
    const interval = setInterval(checkOllama, 5000);
    return () => clearInterval(interval);
  }, [ollamaUrl]);

  async function checkOllama() {
    try {
      const cleanUrl = ollamaUrl.endsWith('/') ? ollamaUrl.slice(0, -1) : ollamaUrl;
      const res = await fetch(`${cleanUrl}/api/tags`);
      if (res.ok) {
        setOllamaConnected(true);
        const data = await res.json();
        setLocalModels(data.models || []);
      } else {
        setOllamaConnected(false);
      }
    } catch {
      setOllamaConnected(false);
    }
  }

  async function handlePullModel(modelName) {
    if (pullingModel) return;
    setPullingModel(modelName);
    setPullProgress(0);
    setPullStatus('Initiating download...');

    try {
      const cleanUrl = ollamaUrl.endsWith('/') ? ollamaUrl.slice(0, -1) : ollamaUrl;
      const response = await fetch(`${cleanUrl}/api/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: modelName })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.status) {
              setPullStatus(data.status);
            }
            if (data.total) {
              const percent = Math.round((data.completed / data.total) * 100);
              setPullProgress(percent);
            }
          } catch (e) {}
        }
      }

      setPullStatus('Model successfully installed! 🎉');
      setPullProgress(100);
      setTimeout(() => {
        setPullingModel(null);
        setPullProgress(0);
        setPullStatus('');
        checkOllama();
      }, 3000);

    } catch (err) {
      setPullStatus(`Download failed: ${err.message}`);
      setTimeout(() => {
        setPullingModel(null);
        setPullProgress(0);
        setPullStatus('');
      }, 5000);
    }
  }

  useEffect(() => {
    if (state.settingsOpen) {
      loadData();
    }
  }, [state.settingsOpen]);

  async function loadData() {
    try {
      const k = await fetchKeys();
      setKeys(k);
      if (k.API_KEYS_QUEUE && k.API_KEYS_QUEUE.queue) {
        setQueueKeys(k.API_KEYS_QUEUE.queue);
      } else {
        setQueueKeys([]);
      }
    } catch {}
  }

  async function handleSave(name) {
    const val = keyInputs[name];
    if (!val) return;
    await saveKey(name, val);
    setKeyInputs(prev => ({ ...prev, [name]: '' }));
    loadData();
  }

  async function handleDelete(name) {
    await removeKey(name);
    loadData();
  }

  async function handleAddQueueKey(e) {
    e.preventDefault();
    if (!label.trim() || !value.trim()) return;
    setAddingToQueue(true);
    try {
      await addQueueKey(provider, label.trim(), value.trim());
      setLabel('');
      setValue('');
      await loadData();
    } catch {}
    setAddingToQueue(false);
  }

  async function handleDeleteQueueKey(keyId) {
    try {
      await removeQueueKey(keyId);
      await loadData();
    } catch {}
  }

  async function handleToggleKey(name) {
    try {
      await toggleKey(name);
      await loadData();
    } catch (err) {
      console.error('Failed to toggle key:', err);
    }
  }

  async function handleToggleQueueKey(keyId) {
    try {
      await toggleQueueKey(keyId);
      await loadData();
    } catch (err) {
      console.error('Failed to toggle queue key:', err);
    }
  }

  if (!state.settingsOpen) return null;

  const keyNames = ['GEMINI_API_KEY', 'HUGGINGFACE_API_KEY', 'GITHUB_TOKEN', 'VERCEL_TOKEN', 'RENDER_TOKEN', 'NEON_API_KEY', 'PROJECTS_DIR'];
  const keyLabels = {
    GEMINI_API_KEY: 'Primary Gemini API Key',
    HUGGINGFACE_API_KEY: 'Hugging Face API Token',
    GITHUB_TOKEN: 'GitHub Personal Access Token',
    VERCEL_TOKEN: 'Vercel API Token',
    RENDER_TOKEN: 'Render API Key',
    NEON_API_KEY: 'Neon Serverless Postgres API Key',
    PROJECTS_DIR: 'Projects Storage Path'
  };

  const keyCreationLinks = {
    GEMINI_API_KEY: 'https://aistudio.google.com/app/apikey',
    HUGGINGFACE_API_KEY: 'https://huggingface.co/settings/tokens',
    GITHUB_TOKEN: 'https://github.com/settings/tokens',
    VERCEL_TOKEN: 'https://vercel.com/account/tokens',
    RENDER_TOKEN: 'https://dashboard.render.com/user/settings#api-keys',
    NEON_API_KEY: 'https://console.neon.tech/app/settings/profile',
  };

  const providerLinks = {
    gemini: 'https://aistudio.google.com/app/apikey',
    openai: 'https://platform.openai.com/api-keys',
    anthropic: 'https://console.anthropic.com/settings/keys',
    groq: 'https://console.groq.com/keys',
    huggingface: 'https://huggingface.co/settings/tokens',
  };

  const providerBadges = {
    gemini: { text: 'Google Gemini', color: '#1a73e8', bg: 'rgba(26, 115, 232, 0.15)' },
    openai: { text: 'OpenAI ChatGPT', color: '#10a37f', bg: 'rgba(16, 163, 127, 0.15)' },
    anthropic: { text: 'Anthropic Claude', color: '#d9775f', bg: 'rgba(217, 119, 95, 0.15)' },
    groq: { text: 'Groq Llama', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
    huggingface: { text: 'Hugging Face', color: '#ffcc00', bg: 'rgba(255, 204, 0, 0.15)' },
  };

  return (
    <>
      <div className="settings-overlay" onClick={() => dispatch({ type: 'CLOSE_SETTINGS' })} />
      <div className="settings-panel">
        <div className="settings-header">
          <h3>⚙️ Settings</h3>
          <button className="settings-close" onClick={() => dispatch({ type: 'CLOSE_SETTINGS' })}>✕</button>
        </div>

        {/* ── FAILOVER QUEUE ── */}
        <div className="settings-section">
          <h4>🔄 API Key Failover Queue</h4>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.5 }}>
            Add backup keys here (Gemini, OpenAI, Claude, Groq, Hugging Face). If a key runs out of quota or rate limits, the chatbot will automatically switch to the next key in this queue and retry seamlessly!
          </p>

          {/* Add Key Form */}
          <form onSubmit={handleAddQueueKey} className="key-card" style={{ background: 'rgba(255,255,255,0.02)', borderStyle: 'dashed' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', gap: 10 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>PROVIDER</label>
                  <select
                    value={provider}
                    onChange={e => setProvider(e.target.value)}
                    style={{
                      width: '100%',
                      padding: 8,
                      background: 'var(--bg-primary)',
                      border: '1px solid var(--border-glass)',
                      borderRadius: 6,
                      color: 'var(--text-primary)',
                      fontSize: 12,
                      fontFamily: 'inherit',
                      outline: 'none'
                    }}
                  >
                    <option value="gemini">Google Gemini</option>
                    <option value="openai">OpenAI (ChatGPT)</option>
                    <option value="anthropic">Anthropic (Claude)</option>
                    <option value="groq">Groq (Llama 3)</option>
                    <option value="huggingface">Hugging Face (Serverless API)</option>
                  </select>
                </div>
                <div style={{ flex: 1.5 }}>
                  <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>KEY NAME / LABEL</label>
                  <input
                    type="text"
                    placeholder="e.g. Backup Gemini Key"
                    value={label}
                    onChange={e => setLabel(e.target.value)}
                    required
                    autoComplete="off"
                    style={{ width: '100%', padding: 8, fontSize: 12 }}
                  />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>API KEY</label>
                  {providerLinks[provider] && (
                    <a 
                      href={providerLinks[provider]} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="get-key-link"
                    >
                      Get API key ↗
                    </a>
                  )}
                </div>
                <input
                  type="password"
                  placeholder="Paste key here..."
                  value={value}
                  onChange={e => setValue(e.target.value)}
                  required
                  autoComplete="new-password"
                  style={{ width: '100%', padding: 8, fontSize: 12 }}
                />
              </div>

              <button
                type="submit"
                disabled={addingToQueue || !label.trim() || !value.trim()}
                className="btn-save-key"
                style={{ width: '100%', padding: '8px 12px', borderRadius: 6, fontSize: 12 }}
              >
                {addingToQueue ? 'Adding...' : '＋ Add to Failover Queue'}
              </button>
            </div>
          </form>

          {/* Queue List */}
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {queueKeys.length === 0 ? (
              <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', padding: '12px 0' }}>
                Queue is empty. Add backup keys above to enable automatic model failover.
              </p>
            ) : (
              queueKeys.map((item, idx) => {
                const badge = providerBadges[item.provider] || { text: item.provider, color: 'var(--text-muted)', bg: 'rgba(255,255,255,0.08)' };
                return (
                  <div key={item.id} className="key-card" style={{ borderLeft: `3px solid ${badge.color}` }}>
                    <div className="key-card-header" style={{ marginBottom: 4 }}>
                      <span className="key-card-name" style={{ gap: 8 }}>
                        <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: badge.bg, color: badge.color, fontWeight: 'bold' }}>
                          {badge.text}
                        </span>
                        <span style={{ fontSize: 13, fontWeight: '500' }}>{item.label}</span>
                      </span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>QUEUE #{idx + 1}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        Preview: {item.preview}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', userSelect: 'none' }}>
                          <input
                            type="checkbox"
                            checked={item.enabled !== false}
                            onChange={() => handleToggleQueueKey(item.id)}
                            style={{ accentColor: 'var(--accent-cyan)', cursor: 'pointer' }}
                          />
                          <span style={{ fontSize: 10, color: item.enabled !== false ? 'var(--accent-cyan)' : 'var(--text-muted)', fontWeight: 'bold' }}>
                            {item.enabled !== false ? 'ACTIVE' : 'DISABLED'}
                          </span>
                        </label>
                        <button
                          onClick={() => handleDeleteQueueKey(item.id)}
                          className="btn-delete-key"
                          style={{ padding: '3px 8px', borderRadius: 4, fontSize: 10, marginTop: 0 }}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ── BASE SYSTEM KEYS ── */}
        <div className="settings-section">
          <h4>🔑 Core Credentials & Config</h4>
          {keyNames.map(name => {
            const info = keys[name] || { configured: false };
            return (
              <div
                key={name}
                id={`key-card-${name}`}
                className="key-card"
                style={highlightedField === name ? {
                  border: '1px solid rgba(239, 68, 68, 0.8)',
                  boxShadow: '0 0 15px rgba(239, 68, 68, 0.35)',
                  background: 'rgba(239, 68, 68, 0.03)',
                  transition: 'all 0.3s ease'
                } : {}}
              >
                <div className="key-card-header">
                  <span className="key-card-name">
                    <span className={`key-status-dot ${info.configured ? 'configured' : 'missing'}`} />
                    {keyLabels[name]}
                  </span>
                  {keyCreationLinks[name] && (
                    <a
                      href={keyCreationLinks[name]}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="get-key-link"
                    >
                      Get API key ↗
                    </a>
                  )}
                </div>
                {info.configured && (
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace', marginBottom: 6 }}>
                    {name === 'PROJECTS_DIR' ? 'Active Path: ' : 'Preview: '}{info.preview}
                  </p>
                )}
                <input
                  type={name === 'PROJECTS_DIR' ? 'text' : 'password'}
                  placeholder={info.configured ? 'Update config...' : (name === 'PROJECTS_DIR' ? 'e.g. C:\\Users\\HP\\Google Drive\\Projects' : 'Enter key...')}
                  value={keyInputs[name] || ''}
                  onChange={e => setKeyInputs(prev => ({ ...prev, [name]: e.target.value }))}
                  autoComplete={name === 'PROJECTS_DIR' ? 'off' : 'new-password'}
                />
                <div className="key-card-actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  {info.configured && name !== 'PROJECTS_DIR' ? (
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', userSelect: 'none' }}>
                      <input
                        type="checkbox"
                        checked={info.enabled !== false}
                        onChange={() => handleToggleKey(name)}
                        style={{ accentColor: 'var(--accent-cyan)', cursor: 'pointer' }}
                      />
                      <span style={{ fontSize: 10, color: info.enabled !== false ? 'var(--accent-cyan)' : 'var(--text-muted)', fontWeight: 'bold' }}>
                        {info.enabled !== false ? 'ACTIVE' : 'DISABLED'}
                      </span>
                    </label>
                  ) : <div />}
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn-save-key" onClick={() => handleSave(name)}>Save</button>
                    {info.configured && (
                      <button className="btn-delete-key" onClick={() => handleDelete(name)}>Delete</button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* ── OLLAMA LOCAL INTEGRATION ── */}
        <div className="settings-section" style={{ marginTop: '20px', borderTop: '1px solid var(--border-glass)', paddingTop: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h4 style={{ margin: 0 }}>
              💻 Ollama Local Engine{' '}
              {isMobileDevice && (
                <span style={{ fontSize: '10px', color: 'var(--accent-amber)', fontWeight: 'bold', marginLeft: '6px' }}>
                  (PCs/Desktops Only)
                </span>
              )}
            </h4>
            <span style={{
              fontSize: 11,
              fontWeight: '600',
              padding: '2px 8px',
              borderRadius: 12,
              background: ollamaConnected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              color: ollamaConnected ? 'var(--accent-green)' : 'var(--accent-red)'
            }}>
              {ollamaConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span>
          </div>

          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.5 }}>
            {isMobileDevice ? (
              "⚠️ Ollama cannot run natively on mobile devices. To connect this phone to local models, you must run Ollama on your PC and configure your PC's IP address or an ngrok/Cloudflare tunnel as your backend URL."
            ) : (
              "Run LLMs locally on your own machine. 100% free, private, and offline. If your primary cloud key runs out of quota, the agent will automatically failover to your active local Ollama model!"
            )}
          </p>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px', fontWeight: '600' }}>
              OLLAMA CONNECTION URL / SECURE TUNNEL
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => handleOllamaUrlChange(e.target.value)}
                placeholder="http://localhost:11434"
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-glass)',
                  background: 'rgba(0, 0, 0, 0.2)',
                  color: '#fff',
                  fontSize: '12px',
                  outline: 'none'
                }}
              />
              {ollamaUrl !== 'http://localhost:11434' && (
                <button
                  onClick={() => handleOllamaUrlChange('http://localhost:11434')}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-glass)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: 'var(--text-secondary)',
                    fontSize: '11px',
                    cursor: 'pointer'
                  }}
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* Expandable Tunnel Guide */}
          <div style={{ marginBottom: '16px' }}>
            <details style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-glass)',
              borderRadius: '6px',
              padding: '8px 12px',
              fontSize: '11px',
              cursor: 'pointer'
            }}>
              <summary style={{
                color: 'var(--accent-cyan)',
                fontWeight: '600',
                outline: 'none',
                userSelect: 'none'
              }}>
                🔗 How to connect local Ollama to secure HTTPS site?
              </summary>
              <div style={{ marginTop: '8px', color: 'var(--text-secondary)', lineHeight: '1.6', cursor: 'default' }}>
                <p style={{ margin: '0 0 8px 0' }}>
                  Secure web browsers block direct local HTTP connections from HTTPS websites. You can bypass this by exposing Ollama through a secure HTTPS tunnel:
                </p>
                <ol style={{ paddingLeft: '16px', margin: '0 0 8px 0' }}>
                  <li style={{ marginBottom: '4px' }}>
                    Install and run <strong>Ollama</strong> on your PC.
                  </li>
                  <li style={{ marginBottom: '4px' }}>
                    Allow CORS requests by launching Ollama with the origin variable set:
                    <ul>
                      <li style={{ margin: '4px 0' }}>
                        <strong>Windows (CMD):</strong>
                        <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px 10px', borderRadius: '4px', fontFamily: 'monospace', fontSize: '10px', color: '#fff', margin: '2px 0' }}>
                          set OLLAMA_ORIGINS=* && ollama serve
                        </div>
                      </li>
                      <li style={{ margin: '4px 0' }}>
                        <strong>Mac/Linux:</strong>
                        <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px 10px', borderRadius: '4px', fontFamily: 'monospace', fontSize: '10px', color: '#fff', margin: '2px 0' }}>
                          OLLAMA_ORIGINS="*" ollama serve
                        </div>
                      </li>
                    </ul>
                  </li>
                  <li style={{ marginBottom: '4px' }}>
                    In another terminal, start a free HTTPS tunnel using <strong>localtunnel</strong>:
                    <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px 10px', borderRadius: '4px', fontFamily: 'monospace', fontSize: '10px', color: '#fff', margin: '4px 0' }}>
                      npx localtunnel --port 11434
                    </div>
                    Or using <strong>ngrok</strong>:
                    <div style={{ background: 'rgba(0,0,0,0.4)', padding: '6px 10px', borderRadius: '4px', fontFamily: 'monospace', fontSize: '10px', color: '#fff', margin: '4px 0' }}>
                      ngrok http 11434
                    </div>
                  </li>
                  <li>
                    Copy the secure <code>https://...</code> URL and paste it into the Ollama connection input above!
                  </li>
                </ol>
              </div>
            </details>
          </div>

          {!ollamaConnected ? (
            <div style={{
              background: 'rgba(239, 68, 68, 0.03)',
              border: '1px dashed rgba(239, 68, 68, 0.25)',
              borderRadius: 8,
              padding: 14,
              textAlign: 'center'
            }}>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '0 0 10px 0' }}>
                Ollama is not running on your computer.
              </p>
              <a
                href="https://ollama.com/download"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-save-key"
                style={{
                  display: 'inline-block',
                  textDecoration: 'none',
                  fontSize: 12,
                  padding: '8px 16px',
                  borderRadius: 6,
                  textAlign: 'center'
                }}
              >
                📥 Download Ollama (80MB Installer) ↗
              </a>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Active Local Models List */}
              <div>
                <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                  INSTALLED LOCAL MODELS ({localModels.length})
                </label>
                {localModels.length === 0 ? (
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0, fontStyle: 'italic' }}>
                    No models installed. Download a model below to get started.
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {localModels.map(m => (
                      <span key={m.name} style={{
                        fontSize: 11,
                        padding: '4px 8px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-glass)',
                        borderRadius: 4,
                        color: 'var(--text-primary)'
                      }}>
                        📦 {m.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Pull Models Manager */}
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 10 }}>
                <label style={{ fontSize: 10, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                  PULL / INSTALL FREE MODELS
                </label>

                {pullingModel ? (
                  <div style={{
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-glass)',
                    borderRadius: 6,
                    padding: 12
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
                      <span style={{ fontWeight: '500' }}>📥 Downloading {pullingModel}...</span>
                      <span style={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}>{pullProgress}%</span>
                    </div>
                    <div style={{
                      width: '100%',
                      height: 6,
                      background: 'rgba(255, 255, 255, 0.08)',
                      borderRadius: 3,
                      overflow: 'hidden',
                      marginBottom: 6
                    }}>
                      <div style={{
                        width: `${pullProgress}%`,
                        height: '100%',
                        background: 'var(--gradient-accent)',
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                    <span style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                      Status: {pullStatus}
                    </span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {/* helper function to check if model is installed */}
                    {(() => {
                      const isModelInstalled = (name) => {
                        return localModels.some(m => m.name === name || m.name.startsWith(name));
                      };

                      return (
                        <>
                          {/* 1.5B Model */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: 8, borderRadius: 6, border: '1px solid var(--border-glass)' }}>
                            <div>
                              <span style={{ fontSize: 12, fontWeight: '600', display: 'block' }}>Qwen 2.5 Coder 1.5B (Offline Light)</span>
                              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Disk: 1.6GB | Download: 900MB | Low-spec PCs</span>
                            </div>
                            {isModelInstalled('qwen2.5-coder:1.5b') ? (
                              <button
                                disabled
                                style={{
                                  padding: '6px 12px',
                                  fontSize: 11,
                                  borderRadius: 4,
                                  marginTop: 0,
                                  background: 'rgba(16, 185, 129, 0.12)',
                                  border: '1px solid rgba(16, 185, 129, 0.25)',
                                  color: 'var(--accent-green)',
                                  cursor: 'not-allowed',
                                  fontWeight: '600'
                                }}
                              >
                                ✓ Installed
                              </button>
                            ) : (
                              <button
                                className="btn-save-key"
                                onClick={() => handlePullModel('qwen2.5-coder:1.5b')}
                                style={{ padding: '6px 12px', fontSize: 11, borderRadius: 4, marginTop: 0 }}
                              >
                                Install
                              </button>
                            )}
                          </div>

                          {/* 7B Model */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: 8, borderRadius: 6, border: '1px solid var(--border-glass)' }}>
                            <div>
                              <span style={{ fontSize: 12, fontWeight: '600', display: 'block' }}>Qwen 2.5 Coder 7B (Recommended)</span>
                              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Disk: 5.2GB | Download: 4.7GB | Mid-spec PCs (6-8GB GPU)</span>
                            </div>
                            {isModelInstalled('qwen2.5-coder:7b') ? (
                              <button
                                disabled
                                style={{
                                  padding: '6px 12px',
                                  fontSize: 11,
                                  borderRadius: 4,
                                  marginTop: 0,
                                  background: 'rgba(16, 185, 129, 0.12)',
                                  border: '1px solid rgba(16, 185, 129, 0.25)',
                                  color: 'var(--accent-green)',
                                  cursor: 'not-allowed',
                                  fontWeight: '600'
                                }}
                              >
                                ✓ Installed
                              </button>
                            ) : (
                              <button
                                className="btn-save-key"
                                onClick={() => handlePullModel('qwen2.5-coder:7b')}
                                style={{ padding: '6px 12px', fontSize: 11, borderRadius: 4, marginTop: 0 }}
                              >
                                Install
                              </button>
                            )}
                          </div>

                          {/* 14B Model */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: 8, borderRadius: 6, border: '1px solid var(--border-glass)' }}>
                            <div>
                              <span style={{ fontSize: 12, fontWeight: '600', display: 'block' }}>Qwen 2.5 Coder 14B (Powerful Coding)</span>
                              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Disk: 10GB | Download: 9GB | High-spec PCs (12GB+ GPU)</span>
                            </div>
                            {isModelInstalled('qwen2.5-coder:14b') ? (
                              <button
                                disabled
                                style={{
                                  padding: '6px 12px',
                                  fontSize: 11,
                                  borderRadius: 4,
                                  marginTop: 0,
                                  background: 'rgba(16, 185, 129, 0.12)',
                                  border: '1px solid rgba(16, 185, 129, 0.25)',
                                  color: 'var(--accent-green)',
                                  cursor: 'not-allowed',
                                  fontWeight: '600'
                                }}
                              >
                                ✓ Installed
                              </button>
                            ) : (
                              <button
                                className="btn-save-key"
                                onClick={() => handlePullModel('qwen2.5-coder:14b')}
                                style={{ padding: '6px 12px', fontSize: 11, borderRadius: 4, marginTop: 0 }}
                              >
                                Install
                              </button>
                            )}
                          </div>

                          {/* Llava 7B Vision Model */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: 8, borderRadius: 6, border: '1px solid var(--border-glass)', marginTop: 8 }}>
                            <div>
                              <span style={{ fontSize: 12, fontWeight: '600', display: 'block' }}>Llava 7B (Offline Vision Light)</span>
                              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Disk: 4.7GB | Download: 4.2GB | Fast & low-resource multimodal</span>
                            </div>
                            {isModelInstalled('llava') ? (
                              <button
                                disabled
                                style={{
                                  padding: '6px 12px',
                                  fontSize: 11,
                                  borderRadius: 4,
                                  marginTop: 0,
                                  background: 'rgba(16, 185, 129, 0.12)',
                                  border: '1px solid rgba(16, 185, 129, 0.25)',
                                  color: 'var(--accent-green)',
                                  cursor: 'not-allowed',
                                  fontWeight: '600'
                                }}
                              >
                                ✓ Installed
                              </button>
                            ) : (
                              <button
                                className="btn-save-key"
                                onClick={() => handlePullModel('llava')}
                                style={{ padding: '6px 12px', fontSize: 11, borderRadius: 4, marginTop: 0 }}
                              >
                                Install
                              </button>
                            )}
                          </div>

                          {/* Llama 3.2 Vision 11B Model */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: 8, borderRadius: 6, border: '1px solid var(--border-glass)', marginTop: 8 }}>
                            <div>
                              <span style={{ fontSize: 12, fontWeight: '600', display: 'block' }}>Llama 3.2 Vision 11B (Offline Vision Rec)</span>
                              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Disk: 7.9GB | Download: 7.2GB | High-quality Meta multimodal</span>
                            </div>
                            {isModelInstalled('llama3.2-vision') ? (
                              <button
                                disabled
                                style={{
                                  padding: '6px 12px',
                                  fontSize: 11,
                                  borderRadius: 4,
                                  marginTop: 0,
                                  background: 'rgba(16, 185, 129, 0.12)',
                                  border: '1px solid rgba(16, 185, 129, 0.25)',
                                  color: 'var(--accent-green)',
                                  cursor: 'not-allowed',
                                  fontWeight: '600'
                                }}
                              >
                                ✓ Installed
                              </button>
                            ) : (
                              <button
                                className="btn-save-key"
                                onClick={() => handlePullModel('llama3.2-vision')}
                                style={{ padding: '6px 12px', fontSize: 11, borderRadius: 4, marginTop: 0 }}
                              >
                                Install
                              </button>
                            )}
                          </div>
                        </>
                      );
                    })()}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
