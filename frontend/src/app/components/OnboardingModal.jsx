'use client';
import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { fetchKeys, saveKey } from '../services/api';

export default function OnboardingModal() {
  const { state, dispatch } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState(1); // 1 = Terms & Auto-download, 2 = Gemini Key
  const [keyInput, setKeyInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [detectedOS, setDetectedOS] = useState(() => {
    if (typeof window !== 'undefined') {
      const userAgent = window.navigator.userAgent.toLowerCase();
      if (userAgent.includes('mac')) return 'macOS';
      if (userAgent.includes('linux')) return 'Linux';
    }
    return 'Windows';
  });

  async function checkOnboardingStatus() {
    try {
      if (typeof window === 'undefined') return;
      
      const onboardingCompleted = localStorage.getItem('devops_concierge_onboarding_completed') === 'true';
      if (onboardingCompleted) {
        return; // Never prompt again after first successful entry or skip
      }
      
      const termsAccepted = localStorage.getItem('devops_concierge_terms_accepted') === 'true';
      const k = await fetchKeys();
      const hasGemini = k.GEMINI_API_KEY && k.GEMINI_API_KEY.configured;

      if (!termsAccepted) {
        setStep(1);
        setIsOpen(true);
      } else if (!hasGemini) {
        setStep(2);
        setIsOpen(true);
      } else {
        localStorage.setItem('devops_concierge_onboarding_completed', 'true');
      }
    } catch (err) {
      console.error('Failed to check onboarding configuration', err);
    }
  }

  useEffect(() => {
    checkOnboardingStatus();
  }, []);


  const getDownloadUrl = () => {
    const userAgent = window.navigator.userAgent.toLowerCase();
    if (userAgent.includes('win')) {
      return 'https://ollama.com/download/OllamaSetup.exe';
    } else if (userAgent.includes('mac')) {
      return 'https://ollama.com/download/Ollama-darwin.zip';
    }
    // Fallback to official download page
    return 'https://ollama.com/download';
  };

  const handleAcceptTerms = (e) => {
    e.preventDefault();
    
    // 1. Mark terms as accepted
    localStorage.setItem('devops_concierge_terms_accepted', 'true');
    
    // 2. Trigger OS-specific Ollama Installer Download programmatically
    const downloadUrl = getDownloadUrl();
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', '');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 3. Go to Step 2 (Gemini Key configuration)
    setStep(2);
  };

  async function handleSaveKey(e) {
    e.preventDefault();
    if (!keyInput.trim()) return;
    setIsSubmitting(true);
    setError('');

    try {
      await saveKey('GEMINI_API_KEY', keyInput.trim());
      localStorage.setItem('devops_concierge_onboarding_completed', 'true');
      setIsOpen(false);
      window.location.reload();
    } catch (err) {
      setError('Failed to save API key. Please check the key and try again.');
    }
    setIsSubmitting(false);
  }

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ zIndex: 1000 }}>
      <div className="auth-modal" style={{ maxWidth: '540px', width: '95%', padding: '30px', maxHeight: '95vh', display: 'flex', flexDirection: 'column', boxSizing: 'border-box' }}>
        
        {/* HEADER */}
        <div style={{ textAlign: 'center', marginBottom: '16px', flexShrink: 0 }}>
          <span style={{ fontSize: '36px' }}>🧠</span>
          <h2 style={{ margin: '8px 0 4px 0', fontSize: '20px', fontWeight: '800', background: 'var(--gradient-accent)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            DevOps Concierge Agent
          </h2>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '8px' }}>
            <span style={{
              fontSize: '10px',
              padding: '3px 8px',
              borderRadius: '10px',
              background: step === 1 ? 'var(--gradient-accent)' : 'rgba(255,255,255,0.08)',
              color: '#fff',
              fontWeight: 'bold'
            }}>
              Step 1: Terms & Installer
            </span>
            <span style={{
              fontSize: '10px',
              padding: '3px 8px',
              borderRadius: '10px',
              background: step === 2 ? 'var(--gradient-accent)' : 'rgba(255,255,255,0.08)',
              color: '#fff',
              fontWeight: 'bold'
            }}>
              Step 2: Cloud Activation
            </span>
          </div>
        </div>

        {/* STEP 1: TERMS, NEW FEATURES & CONDITIONS */}
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            
            {/* NEW FEATURES HIGHLIGHT */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-glass)',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '14px',
              flexShrink: 0
            }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--accent-cyan)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                🚀 What's New in v2.0
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px' }}>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <span>⚡</span>
                  <div>
                    <strong style={{ color: '#fff' }}>Parallel Streams</strong>
                    <p style={{ margin: '2px 0 0 0', color: 'var(--text-muted)', fontSize: '10px' }}>Send prompts concurrently; stream answers together.</p>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <span>⏳</span>
                  <div>
                    <strong style={{ color: '#fff' }}>Sequential Queue</strong>
                    <p style={{ margin: '2px 0 0 0', color: 'var(--text-muted)', fontSize: '10px' }}>Dependent tasks queue up and run automatically.</p>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <span>🧠</span>
                  <div>
                    <strong style={{ color: '#fff' }}>Adaptive Memory</strong>
                    <p style={{ margin: '2px 0 0 0', color: 'var(--text-muted)', fontSize: '10px' }}>Synthesizes a user profile to personalize tone.</p>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <span>💻</span>
                  <div>
                    <strong style={{ color: '#fff' }}>Local Offline Failover</strong>
                    <p style={{ margin: '2px 0 0 0', color: 'var(--text-muted)', fontSize: '10px' }}>Fails over to Ollama if cloud API keys run out.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Scrollable Terms Textarea */}
            <div style={{
              flex: '1 1 auto',
              overflowY: 'auto',
              border: '1px solid var(--border-glass)',
              borderRadius: '8px',
              background: 'rgba(0,0,0,0.4)',
              padding: '12px 14px',
              fontSize: '11px',
              color: 'var(--text-secondary)',
              lineHeight: '1.5',
              marginBottom: '16px',
              maxHeight: '150px'
            }}>
              <h4 style={{ color: '#fff', margin: '0 0 4px 0', fontSize: '11px' }}>1. Privacy-First Local Architecture</h4>
              <p style={{ margin: '0 0 10px 0' }}>
                All generated code, shell commands, database credentials, and system configurations are processed locally. By default, no proprietary data is uploaded to cloud servers.
              </p>

              <h4 style={{ color: '#fff', margin: '0 0 4px 0', fontSize: '11px' }}>2. Automatic Local Companion Engine</h4>
              <p style={{ margin: '0 0 10px 0' }}>
                Accepting these terms initiates a direct download of the official **Ollama Local Engine** installer ({detectedOS} package). Ollama runs locally on your PC, allowing you to execute tasks completely free, private, and with no rate limits.
              </p>

              <h4 style={{ color: '#fff', margin: '0 0 4px 0', fontSize: '11px' }}>3. Hybrid Cloud Failover Queue</h4>
              <p style={{ margin: '0 0 4px 0' }}>
                Optional cloud API keys supplied by the user are saved securely. If cloud services hit rate limits or quota caps, the system will automatically failover to your local Ollama engine.
              </p>
            </div>

            <button
              onClick={handleAcceptTerms}
              style={{
                padding: '12px',
                borderRadius: '8px',
                background: 'var(--gradient-accent)',
                color: '#fff',
                border: 'none',
                fontWeight: '600',
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: 'var(--shadow-glow)',
                flexShrink: 0
              }}
            >
              ✓ Accept & Download Local Companion ({detectedOS})
            </button>
          </div>
        )}

        {/* STEP 2: CLOUD API KEY */}
        {step === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{
              background: 'rgba(16, 185, 129, 0.08)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
              fontSize: '12px',
              color: 'var(--accent-green)',
              lineHeight: '1.4'
            }}>
              📥 <strong>Local engine installer is downloading in the background!</strong>
              <br />
              While it is installing, try this application using your API key. Or wait until the installation completes to run completely offline.
              <div style={{ marginTop: '8px', fontSize: '11px', color: 'rgba(255,255,255,0.7)', borderTop: '1px solid rgba(16, 185, 129, 0.2)', paddingTop: '6px' }}>
                🔒 <strong>Privacy Note:</strong> If your browser asks to <em>"Access other apps on this device"</em>, you can click <strong>"Allow"</strong> to connect to your local Ollama engine, or click <strong>"Block"</strong> to proceed using cloud API keys. Both methods are safe and fully supported!
              </div>
            </div>



            <form onSubmit={handleSaveKey} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: '600' }}>
                    Primary Gemini API Key
                  </label>
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="get-key-link"
                    style={{ fontSize: '12px' }}
                  >
                    Get your API key ↗
                  </a>
                </div>
                <input
                  type="password"
                  placeholder="Paste your Gemini API Key (AIzaSy...)"
                  value={keyInput}
                  onChange={e => setKeyInput(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-glass)',
                    background: 'rgba(0, 0, 0, 0.3)',
                    color: '#fff',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
                {error && (
                  <p style={{ color: 'var(--accent-red)', fontSize: '12px', marginTop: '6px', margin: '6px 0 0 0' }}>
                    {error}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !keyInput.trim()}
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  background: 'var(--gradient-accent)',
                  color: '#fff',
                  border: 'none',
                  fontWeight: '600',
                  fontSize: '13px',
                  cursor: 'pointer',
                  opacity: (isSubmitting || !keyInput.trim()) ? 0.6 : 1
                }}
              >
                {isSubmitting ? 'Saving Key...' : 'Save & Enter Workspace'}
              </button>
            </form>

            <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-glass)', paddingTop: '16px', textAlign: 'center' }}>
              <button
                onClick={() => {
                  localStorage.setItem('devops_concierge_onboarding_completed', 'true');
                  setIsOpen(false);
                  dispatch({ type: 'TOGGLE_SETTINGS' });
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent-cyan)',
                  fontSize: '12px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  textDecoration: 'underline'
                }}
              >
                Skip cloud key, run completely offline with local Ollama 💻
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
