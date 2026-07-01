'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { 
  streamChat, 
  fetchModels, 
  pauseAgent, 
  resumeAgent, 
  stopAgent,
  fetchKeys,
  selectFolder,
  devopsPush,
  devopsDeployVercel,
  devopsDeployRender
} from '../services/api';

export default function InputBar() {
  const { state, dispatch } = useApp();
  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState([]); // Array of { id, name, base64 }
  const [showVisionWarning, setShowVisionWarning] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const activeControllersRef = useRef({}); // Track active streams: { [msgId]: AbortController }
  const activeTimeoutsRef = useRef({}); // Track active timeouts for basic query wake-up notes

  // DevOps Automation States
  const [keys, setKeys] = useState({});
  const [projectPath, setProjectPath] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [inputGithubUrl, setInputGithubUrl] = useState('');
  const [showFolderModal, setShowFolderModal] = useState(false);
  const [inputFolderPath, setInputFolderPath] = useState('');
  const [automationState, setAutomationState] = useState({ loading: false, error: '', success: '', type: '' });

  const [isMobileDevice, setIsMobileDevice] = useState(() => {
    if (typeof window !== 'undefined') {
      const ua = window.navigator.userAgent.toLowerCase();
      return /android|iphone|ipad|ipod|windows phone/i.test(ua);
    }
    return false;
  });

  useEffect(() => {
    // Load persisted settings
    if (typeof window !== 'undefined') {
      setProjectPath(localStorage.getItem('devops_current_project_path') || '');
      setGithubUrl(localStorage.getItem('devops_current_github_url') || '');
    }

    const loadKeys = async () => {
      try {
        const k = await fetchKeys();
        setKeys(k || {});
      } catch (err) {
        console.error('Failed to fetch keys in InputBar:', err);
      }
    };

    loadKeys();
    const interval = setInterval(loadKeys, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveFolderPath = (e) => {
    e.preventDefault();
    setProjectPath(inputFolderPath);
    if (typeof window !== 'undefined') {
      localStorage.setItem('devops_current_project_path', inputFolderPath);
    }
    setShowFolderModal(false);
    setAutomationState({ loading: false, error: '', success: `Manually set folder to: ${inputFolderPath}`, type: 'folder' });
  };

  const handleSelectFolder = async () => {
    if (isMobileDevice) {
      setInputFolderPath(projectPath);
      setShowFolderModal(true);
      return;
    }
    setAutomationState({ loading: true, error: '', success: '', type: 'folder' });
    try {
      const res = await selectFolder();
      if (res && res.success && res.path) {
        setProjectPath(res.path);
        localStorage.setItem('devops_current_project_path', res.path);
        setAutomationState({ loading: false, error: '', success: `Selected folder: ${res.path}`, type: 'folder' });
      } else {
        setAutomationState({ loading: false, error: res?.error || 'Folder selection cancelled.', success: '', type: 'folder' });
        setInputFolderPath(projectPath);
        setShowFolderModal(true);
      }
    } catch (err) {
      setAutomationState({ loading: false, error: err.message || 'Failed to select folder', success: '', type: 'folder' });
      setInputFolderPath(projectPath);
      setShowFolderModal(true);
    }
  };

  const handlePushToGithub = async () => {
    if (!projectPath) {
      setAutomationState({ loading: false, error: 'Please select a Project Folder first!', success: '', type: 'push' });
      return;
    }
    setAutomationState({ loading: true, error: '', success: '', type: 'push' });
    try {
      const folderName = projectPath.split(/[\\/]/).pop() || 'devops-concierge-project';
      const res = await devopsPush(projectPath, folderName, false);
      if (res && res.success) {
        setGithubUrl(res.repo_url);
        localStorage.setItem('devops_current_github_url', res.repo_url);
        setAutomationState({ 
          loading: false, 
          error: '', 
          success: `Successfully pushed to GitHub! Repository: ${res.repo_url}`, 
          type: 'push' 
        });
      } else {
        setAutomationState({ loading: false, error: res?.error || 'Failed to push to GitHub.', success: '', type: 'push' });
      }
    } catch (err) {
      setAutomationState({ loading: false, error: err.message || 'Failed to push to GitHub', success: '', type: 'push' });
    }
  };

  const handleDeployToVercel = async () => {
    if (!githubUrl) {
      setAutomationState({ loading: false, error: 'First initialize on GitHub!', success: '', type: 'vercel' });
      return;
    }
    setAutomationState({ loading: true, error: '', success: '', type: 'vercel' });
    try {
      const res = await devopsDeployVercel(githubUrl);
      if (res && res.success) {
        setAutomationState({ 
          loading: false, 
          error: '', 
          success: `Successfully deployed to Vercel! Live URL: ${res.url}`, 
          type: 'vercel' 
        });
      } else {
        setAutomationState({ loading: false, error: res?.error || 'Failed to deploy to Vercel.', success: '', type: 'vercel' });
      }
    } catch (err) {
      setAutomationState({ loading: false, error: err.message || 'Failed to deploy to Vercel', success: '', type: 'vercel' });
    }
  };

  const handleDeployToRender = async () => {
    if (!githubUrl) {
      setAutomationState({ loading: false, error: 'First initialize on GitHub!', success: '', type: 'render' });
      return;
    }
    setAutomationState({ loading: true, error: '', success: '', type: 'render' });
    try {
      const res = await devopsDeployRender(githubUrl);
      if (res && res.success) {
        setAutomationState({ 
          loading: false, 
          error: '', 
          success: `Successfully deployed to Render! Service Dashboard: ${res.deploy_url}`, 
          type: 'render' 
        });
      } else {
        setAutomationState({ loading: false, error: res?.error || 'Failed to deploy to Render.', success: '', type: 'render' });
      }
    } catch (err) {
      setAutomationState({ loading: false, error: err.message || 'Failed to deploy to Render', success: '', type: 'render' });
    }
  };

  const handleSaveGithubUrl = (e) => {
    e.preventDefault();
    const url = inputGithubUrl.trim();
    setGithubUrl(url);
    localStorage.setItem('devops_current_github_url', url);
    setShowLinkModal(false);
  };


  // Check vision capabilities and open camera or display warning
  const handleCameraClick = useCallback(async () => {
    try {
      const modelsList = await fetchModels();
      
      // Check if Gemini is configured/available, OR if any local vision model is installed
      const hasGemini = modelsList.some(m => m.id.startsWith('gemini') && m.available !== false);
      const hasLocalVision = modelsList.some(m => {
        const idLower = m.id.toLowerCase();
        const isLocal = m.tier === 'local';
        const isVision = ['llava', 'vision', 'vl', 'minicpm'].some(k => idLower.includes(k));
        return isLocal && isVision && m.available !== false;
      });
      
      if (!hasGemini && !hasLocalVision) {
        setShowVisionWarning(true);
      } else {
        fileInputRef.current?.click();
      }
    } catch (err) {
      // Fallback: just open file picker if API check fails
      fileInputRef.current?.click();
    }
  }, []);

  // Handle image paste (Ctrl+V) in the textarea
  const handlePaste = useCallback((e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        e.preventDefault(); // Prevent pasting raw file paths/text
        const file = items[i].getAsFile();
        if (file) {
          const reader = new FileReader();
          reader.onloadend = () => {
            setAttachments(prev => [
              ...prev,
              {
                id: 'paste_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
                name: file.name || 'Pasted Image',
                base64: reader.result
              }
            ]);
          };
          reader.readAsDataURL(file);
        }
      }
    }
  }, []);

  // Handle files chosen via file picker
  const handleFileChange = useCallback((e) => {
    const files = Array.from(e.target.files || []);
    files.forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onloadend = () => {
          setAttachments(prev => [
            ...prev,
            {
              id: 'file_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
              name: file.name,
              base64: reader.result
            }
          ]);
        };
        reader.readAsDataURL(file);
      }
    });
    // Clear input value so the same file can be picked again if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Synthesize user preferences and memory from chat messages
  const synthesizeUserMemory = useCallback((messages) => {
    if (!messages || messages.length === 0) return '';
    const userMessages = messages.filter(m => m.role === 'user').map(m => m.content);
    const uniqueTags = new Set();
    const text = userMessages.join(' ').toLowerCase();

    if (text.includes('next.js') || text.includes('nextjs')) uniqueTags.add('Next.js framework');
    if (text.includes('typescript') || text.includes('ts')) uniqueTags.add('TypeScript language');
    if (text.includes('postgres') || text.includes('neon')) uniqueTags.add('Neon Serverless Postgres');
    if (text.includes('sqlite')) uniqueTags.add('SQLite database');
    if (text.includes('vercel')) uniqueTags.add('Vercel hosting');
    if (text.includes('github') || text.includes('git')) uniqueTags.add('GitHub deployment');
    if (text.includes('tailwind')) uniqueTags.add('Tailwind CSS styling');
    if (text.includes('fastapi') || text.includes('python')) uniqueTags.add('FastAPI / Python backend');
    if (text.includes('concise') || text.includes('short')) uniqueTags.add('Concise responses');

    let memory = `User has engaged in ${userMessages.length} interaction turns.\n`;
    if (uniqueTags.size > 0) {
      memory += `Detected Preferences: ${Array.from(uniqueTags).join(', ')}.\n`;
    }
    const recentPrompts = userMessages.slice(-3);
    if (recentPrompts.length > 0) {
      memory += `Recent Prompts:\n` + recentPrompts.map(p => `- ${p}`).join('\n');
    }
    return memory;
  }, []);

  // Primary messaging sender
  const sendMessage = useCallback((message, assistantMsgId = null, images = null) => {
    const msgId = assistantMsgId || 'msg_assistant_' + Date.now();
    const sessionId = 'single_session';

    // 1. Fetch user memory from localStorage
    let userMemory = '';
    if (typeof window !== 'undefined') {
      userMemory = localStorage.getItem('devops_concierge_user_profile') || '';
    }

    // Check if it is a basic query to reply instantly
    const cleanMsg = message.toLowerCase().trim().replace(/[?.!,]/g, '');
    const greetings = ['hi', 'hello', 'hy', 'hey', 'yo', 'hola', 'greetings', 'morning', 'afternoon', 'evening'];
    const identity = ['who are you', 'what is this', 'what are you', 'tell me about yourself', 'what do you do', 'your name', 'who created you', 'who build you'];
    const isGreeting = greetings.includes(cleanMsg);
    const isIdentity = identity.some(phrase => cleanMsg.includes(phrase));
    const isBasic = isGreeting || isIdentity;

    let cleanContent = '';
    if (isGreeting) {
      cleanContent = "Hello! I am your DevOps Concierge Agent. How can I help you today? 🚀";
    } else if (isIdentity) {
      cleanContent = "I am the DevOps Concierge Agent developed by **Divyansh Tiwari**—a specialized AI assistant designed to automate repository setup, Git workflows, and cloud deployments (Vercel & Render) directly from your workspace. 💻\n\nCheck out my creator's portfolio: **[Divyansh Tiwari's Portfolio ↗](https://divyansh-tiwari.xyz/)**";
    }

    // 2. Pre-create the assistant message bubble
    dispatch({
      type: 'ADD_MESSAGE',
      sessionId,
      payload: { id: msgId, role: 'assistant', content: cleanContent }
    });

    // 3. Mark streaming status as active
    dispatch({ type: 'SET_STREAMING', payload: true });
    dispatch({ type: 'SET_AGENT_STATE', payload: 'running' });

    const toolCardIds = {};
    let hasReceivedServerResponse = false;

    // Start a timeout to show the wake-up note if the server doesn't respond quickly
    if (isBasic) {
      const tid = setTimeout(() => {
        if (!hasReceivedServerResponse) {
          const wakeUpNote = "\n\n*(Note: I am replying instantly from my local memory while the cloud backend server wakes up on Render...)*";
          dispatch({
            type: 'UPDATE_MESSAGE_BY_ID',
            sessionId,
            messageId: msgId,
            payload: cleanContent + wakeUpNote,
          });
        }
        delete activeTimeoutsRef.current[msgId];
      }, 5000);
      activeTimeoutsRef.current[msgId] = tid;
    }

    // 4. Initiate stream
    const controller = streamChat(message, sessionId, 'auto', userMemory, (event) => {
      switch (event.type) {
        case 'agent_state':
          dispatch({ type: 'SET_AGENT_STATE', payload: event.state });
          break;
        case 'text':
          hasReceivedServerResponse = true;
          if (activeTimeoutsRef.current[msgId]) {
            clearTimeout(activeTimeoutsRef.current[msgId]);
            delete activeTimeoutsRef.current[msgId];
          }
          dispatch({
            type: 'UPDATE_MESSAGE_BY_ID',
            sessionId,
            messageId: msgId,
            payload: event.content,
          });
          break;

        case 'tool_start': {
          const cardId = 'tool_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
          if (event.call_id) {
            toolCardIds[event.call_id] = cardId;
          } else {
            toolCardIds[event.tool] = cardId;
          }
          dispatch({
            type: 'ADD_TOOL_CARD',
            sessionId,
            payload: {
              id: cardId,
              toolName: event.tool,
              status: 'running',
              arguments: event.arguments
            },
          });
          break;
        }

        case 'tool_result': {
          const cardId = event.call_id ? toolCardIds[event.call_id] : toolCardIds[event.tool];
          dispatch({
            type: 'UPDATE_TOOL_CARD',
            sessionId,
            payload: {
              messageId: cardId,
              toolName: event.tool,
              status: (event.result?.error || event.result?.status === 'denied') ? 'error' : 'success',
              result: event.result,
            },
          });
          break;
        }

        case 'tool_approved': {
          const cardId = event.call_id ? toolCardIds[event.call_id] : toolCardIds[event.tool];
          dispatch({
            type: 'UPDATE_TOOL_CARD',
            sessionId,
            payload: { messageId: cardId, toolName: event.tool, status: 'running' },
          });
          break;
        }

        case 'tool_denied': {
          const cardId = event.call_id ? toolCardIds[event.call_id] : toolCardIds[event.tool];
          dispatch({
            type: 'UPDATE_TOOL_CARD',
            sessionId,
            payload: {
              messageId: cardId,
              toolName: event.tool,
              status: 'error',
              result: { message: 'Denied by user' }
            },
          });
          break;
        }

        case 'ui_event':
          if (event.action === 'open_settings') {
            dispatch({ type: 'OPEN_SETTINGS' });
            if (event.highlight_field) {
              const customEvt = new CustomEvent('highlight-setting-field', {
                detail: { field: event.highlight_field }
              });
              window.dispatchEvent(customEvt);
            }
          }
          break;

        case 'auth_request':
          dispatch({ type: 'SET_AUTH_REQUEST', payload: event });
          break;

        case 'error': {
          if (activeTimeoutsRef.current[msgId]) {
            clearTimeout(activeTimeoutsRef.current[msgId]);
            delete activeTimeoutsRef.current[msgId];
          }
          if (isBasic) {
            const fallbackNote = "\n\n*(Note: Cloud backend server is offline or waking up on Render. Running in local frontend fallback mode.)*";
            dispatch({
              type: 'UPDATE_MESSAGE_BY_ID',
              sessionId,
              messageId: msgId,
              payload: cleanContent + fallbackNote,
            });
            dispatch({ type: 'SET_STREAMING', payload: false });
            dispatch({ type: 'SET_AGENT_STATE', payload: null });
            delete activeControllersRef.current[msgId];
            break;
          }

          const isQuotaExhausted = event.content.toLowerCase().includes('keys') || 
                                   event.content.toLowerCase().includes('quota') || 
                                   event.content.toLowerCase().includes('rate limit') ||
                                   event.content.toLowerCase().includes('exceeded');
          
          if (isQuotaExhausted) {
            fetch('http://localhost:11434/api/tags')
              .then(res => {
                if (res.ok) {
                  return res.json();
                }
                throw new Error('Not running');
              })
              .then(data => {
                const models = data.models || [];
                const has1_5b = models.some(m => m.name.startsWith('qwen2.5-coder:1.5b') || m.name.startsWith('qwen2.5-coder:latest'));
                
                if (has1_5b) {
                  dispatch({ type: 'SET_MODEL', payload: 'qwen2.5-coder:1.5b' });
                  dispatch({
                    type: 'UPDATE_MESSAGE_BY_ID',
                    sessionId,
                    messageId: msgId,
                    payload: `⚠️ **Cloud API limits exceeded!** We have automatically switched you to your offline Local Ollama model (**Qwen 2.5 Coder 1.5B**) which is ready to run 100% free, private, and unlimited! Please resend your prompt.`,
                  });
                } else {
                  dispatch({
                    type: 'UPDATE_MESSAGE_BY_ID',
                    sessionId,
                    messageId: msgId,
                    payload: `⚠️ **Cloud API limits exceeded!** We detected Ollama is running, but you don't have the lightweight coding model installed yet. Open the ⚙️ Settings panel to download **Qwen 2.5 Coder 1.5B** (900MB) with 1-click and run 100% offline!`,
                  });
                }
              })
              .catch(() => {
                dispatch({
                  type: 'UPDATE_MESSAGE_BY_ID',
                  sessionId,
                  messageId: msgId,
                  payload: `⚠️ **Cloud API limits exceeded!** To continue chatting completely free, private, and offline, please download the **Ollama app** (80MB installer) from [ollama.com](https://ollama.com/download), run it, and install the model in your ⚙️ Settings!`,
                });
              });
          } else {
            dispatch({
              type: 'UPDATE_MESSAGE_BY_ID',
              sessionId,
              messageId: msgId,
              payload: `⚠️ ${event.content}`,
            });
          }
          break;
        }

        case 'done':
          if (activeTimeoutsRef.current[msgId]) {
            clearTimeout(activeTimeoutsRef.current[msgId]);
            delete activeTimeoutsRef.current[msgId];
          }
          delete activeControllersRef.current[msgId];
          const activeCount = Object.keys(activeControllersRef.current).length;
          
          if (activeCount === 0) {
            dispatch({ type: 'SET_STREAMING', payload: false });
            if (state.agentState !== 'stopped') {
              dispatch({ type: 'SET_AGENT_STATE', payload: null });
            }
          }

          if (typeof window !== 'undefined') {
            const currentMsgs = JSON.parse(localStorage.getItem('devops_concierge_chat_history') || '[]');
            const updatedMemory = synthesizeUserMemory(currentMsgs);
            localStorage.setItem('devops_concierge_user_profile', updatedMemory);
          }
          break;
      }
    }, images);

    activeControllersRef.current[msgId] = controller;
  }, [state.model, state.agentState, dispatch, synthesizeUserMemory]);

  // Stop active streaming responses
  const handleStop = useCallback(() => {
    Object.keys(activeControllersRef.current).forEach(msgId => {
      const controller = activeControllersRef.current[msgId];
      if (controller && typeof controller.abort === 'function') {
        controller.abort();
      }
      delete activeControllersRef.current[msgId];
    });
    Object.keys(activeTimeoutsRef.current).forEach(msgId => {
      clearTimeout(activeTimeoutsRef.current[msgId]);
      delete activeTimeoutsRef.current[msgId];
    });
    dispatch({ type: 'SET_STREAMING', payload: false });
    dispatch({ type: 'SET_AGENT_STATE', payload: 'stopped' });
  }, [dispatch]);

  // Dependency checking heuristic
  const checkDependency = (messageText) => {
    const sequentialKeywords = [
      'deploy', 'push', 'github', 'vercel', 'db', 'it', 'that', 'this', 'them', 
      'now', 'then', 'run', 'previous', 'scaffolded', 'configure', 'setup',
      'database', 'repo', 'repository', 'docs', 'document', 'publish'
    ];
    const lower = messageText.toLowerCase();
    return sequentialKeywords.some(keyword => lower.includes(keyword));
  };

  // Submit button handler
  const handleSubmit = useCallback(async () => {
    const message = input.trim();
    const imgBase64s = attachments.map(a => a.base64);
    if (!message && imgBase64s.length === 0) return;

    setInput('');
    setAttachments([]);
    
    // Reset textarea height
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
    }

    const sessionId = 'single_session';
    const activeStreams = Object.keys(activeControllersRef.current).length;

    if (activeStreams > 0) {
      // An operation is currently running! Check dependencies
      const isDependent = checkDependency(message);

      if (isDependent) {
        // 1. Add user message with local image previews in tool_data
        dispatch({
          type: 'ADD_MESSAGE',
          sessionId,
          payload: { 
            id: 'msg_' + Date.now(), 
            role: 'user', 
            content: message,
            tool_data: imgBase64s.length > 0 ? { images: imgBase64s } : null
          }
        });
        // 2. Add system warning notice
        dispatch({
          type: 'ADD_MESSAGE',
          sessionId,
          payload: {
            role: 'system_notice',
            content: '⚠️ First previous task must be completed. This prompt has been added to the queue to be handled sequentially.'
          }
        });
        // 3. Add to sequential queue (preserving images!)
        dispatch({
          type: 'ADD_TO_QUEUE',
          payload: { id: 'queued_' + Date.now(), content: message, images: imgBase64s }
        });
      } else {
        // Independent task: offer parallel choice card
        dispatch({
          type: 'ADD_MESSAGE',
          sessionId,
          payload: { 
            id: 'msg_' + Date.now(), 
            role: 'user', 
            content: message,
            tool_data: imgBase64s.length > 0 ? { images: imgBase64s } : null
          }
        });
        dispatch({
          type: 'ADD_MESSAGE',
          sessionId,
          payload: {
            id: 'choice_' + Date.now(),
            role: 'system_choice',
            content: message,
            pending: true
          }
        });
      }
    } else {
      // No active task: send immediately
      dispatch({
        type: 'ADD_MESSAGE',
        sessionId,
        payload: { 
          id: 'msg_' + Date.now(), 
          role: 'user', 
          content: message,
          tool_data: imgBase64s.length > 0 ? { images: imgBase64s } : null
        }
      });
      sendMessage(message, null, imgBase64s);
    }
  }, [input, attachments, dispatch, sendMessage]);

  // Listener for SET_RETRY starter prompts and choices
  useEffect(() => {
    if (state.retryMessage) {
      const { message, runParallel } = state.retryMessage;
      dispatch({ type: 'CLEAR_RETRY' });

      if (runParallel) {
        sendMessage(message);
      } else {
        const activeStreams = Object.keys(activeControllersRef.current).length;
        if (activeStreams > 0) {
          if (checkDependency(message)) {
            dispatch({
              type: 'ADD_MESSAGE',
              sessionId: 'single_session',
              payload: {
                role: 'system_notice',
                content: '⚠️ First previous task must be completed. This prompt has been added to the queue to be handled sequentially.'
              }
            });
            dispatch({
              type: 'ADD_TO_QUEUE',
              payload: { id: 'queued_' + Date.now(), content: message }
            });
          } else {
            dispatch({
              type: 'ADD_MESSAGE',
              sessionId: 'single_session',
              payload: {
                id: 'choice_' + Date.now(),
                role: 'system_choice',
                content: message,
                pending: true
              }
            });
          }
        } else {
          sendMessage(message);
        }
      }
    }
  }, [state.retryMessage, dispatch, sendMessage]);

  // Silent background puller for qwen2.5-coder:1.5b
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const res = await fetch('http://localhost:11434/api/tags');
        if (!res.ok) return;
        
        const data = await res.json();
        const models = data.models || [];
        const hasModel = models.some(m => m.name.startsWith('qwen2.5-coder:1.5b') || m.name.startsWith('qwen2.5-coder:latest'));
        
        if (!hasModel) {
          console.log('[Ollama Background] qwen2.5-coder:1.5b not found. Silently pulling in background...');
          fetch('http://localhost:11434/api/pull', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'qwen2.5-coder:1.5b', stream: false })
          }).catch(() => {});
        }
      } catch (err) {}
    }, 5000);
    
    return () => clearTimeout(timer);
  }, []);

  // Automated Sequential Dequeueing Effect
  useEffect(() => {
    const activeStreams = Object.keys(activeControllersRef.current).length;
    if (activeStreams === 0 && !state.isStreaming && state.promptQueue.length > 0) {
      const nextTask = state.promptQueue[0];
      dispatch({ type: 'DEQUEUE' });

      dispatch({
        type: 'ADD_MESSAGE',
        sessionId: 'single_session',
        payload: { role: 'system_notice', content: `🚀 Starting queued task: "${nextTask.content}"...` }
      });

      // Pass the queued task's images along!
      sendMessage(nextTask.content, null, nextTask.images || null);
    }
  }, [state.isStreaming, state.promptQueue, dispatch, sendMessage]);

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleInput(e) {
    setInput(e.target.value);
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
    }
  }

  return (
    <div className="input-bar-container">
      {/* 🛠️ PREMIUM AGENT CONTROL PANEL */}
      {(state.agentState === 'running' || state.agentState === 'paused' || state.agentState === 'stopped') && (
        <div 
          className="agent-control-panel animate-slide-up"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            padding: '10px 18px',
            background: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(6, 182, 212, 0.25)',
            borderRadius: '30px',
            marginBottom: '12px',
            maxWidth: '500px',
            margin: '0 auto 12px auto',
            boxShadow: '0 8px 32px rgba(6, 182, 212, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="control-pulse-dot" style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: state.agentState === 'running' ? 'var(--accent-cyan)' : state.agentState === 'paused' ? '#eab308' : '#ef4444',
              boxShadow: state.agentState === 'running' 
                ? '0 0 10px var(--accent-cyan)' 
                : state.agentState === 'paused' 
                  ? '0 0 10px #eab308' 
                  : '0 0 10px #ef4444',
            }} />
            <span style={{ fontSize: '12px', fontWeight: '600', color: '#fff', textTransform: 'capitalize' }}>
              Agent {state.agentState}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {state.agentState === 'running' && (
              <button
                onClick={async () => {
                  try {
                    await pauseAgent(state.currentSessionId);
                    dispatch({ type: 'SET_AGENT_STATE', payload: 'paused' });
                  } catch (e) {
                    console.error(e);
                  }
                }}
                style={{
                  background: 'rgba(234, 179, 8, 0.15)',
                  border: '1px solid rgba(234, 179, 8, 0.4)',
                  borderRadius: '20px',
                  padding: '4px 12px',
                  color: '#fef08a',
                  fontSize: '11px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(234, 179, 8, 0.25)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(234, 179, 8, 0.15)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                ⏸️ Pause
              </button>
            )}

            {state.agentState === 'paused' && (
              <button
                onClick={async () => {
                  try {
                    await resumeAgent(state.currentSessionId);
                    dispatch({ type: 'SET_AGENT_STATE', payload: 'running' });
                  } catch (e) {
                    console.error(e);
                  }
                }}
                style={{
                  background: 'rgba(34, 197, 94, 0.15)',
                  border: '1px solid rgba(34, 197, 94, 0.4)',
                  borderRadius: '20px',
                  padding: '4px 12px',
                  color: '#bbf7d0',
                  fontSize: '11px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(34, 197, 94, 0.25)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(34, 197, 94, 0.15)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                ▶️ Resume
              </button>
            )}

            {(state.agentState === 'running' || state.agentState === 'paused') && (
              <button
                onClick={async () => {
                  try {
                    await stopAgent(state.currentSessionId);
                    handleStop();
                  } catch (e) {
                    console.error(e);
                  }
                }}
                style={{
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  borderRadius: '20px',
                  padding: '4px 12px',
                  color: '#fecaca',
                  fontSize: '11px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                🛑 Stop
              </button>
            )}

            {state.agentState === 'stopped' && (
              <button
                onClick={() => {
                  const msgs = state.messages['single_session'] || [];
                  const lastUserMsg = [...msgs].reverse().find(m => m.role === 'user');
                  if (lastUserMsg) {
                    dispatch({ type: 'REMOVE_LAST_ASSISTANT', sessionId: 'single_session' });
                    sendMessage(lastUserMsg.content);
                  }
                }}
                style={{
                  background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(59, 130, 246, 0.2) 100%)',
                  border: '1px solid rgba(6, 182, 212, 0.5)',
                  borderRadius: '20px',
                  padding: '4px 14px',
                  color: '#fff',
                  fontSize: '11px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 0 10px rgba(6, 182, 212, 0.3)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.transform = 'translateY(-1px) scale(1.02)';
                  e.currentTarget.style.boxShadow = '0 0 15px rgba(6, 182, 212, 0.5)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.transform = 'translateY(0) scale(1)';
                  e.currentTarget.style.boxShadow = '0 0 10px rgba(6, 182, 212, 0.3)';
                }}
              >
                🔄 Retry with New Approach
              </button>
            )}
          </div>
        </div>
      )}

      {/* 📸 ATTACHMENTS PREVIEW DRAWER */}
      {attachments.length > 0 && (
        <div 
          className="input-attachments-preview"
          style={{
            display: 'flex',
            gap: '12px',
            padding: '10px 12px',
            background: 'rgba(19, 24, 41, 0.55)',
            border: '1px solid var(--border-glass)',
            borderRadius: '12px',
            marginBottom: '10px',
            overflowX: 'auto',
            maxWidth: '780px',
            margin: '0 auto 10px auto'
          }}
        >
          {attachments.map((file) => (
            <div 
              key={file.id}
              style={{
                position: 'relative',
                width: '74px',
                height: '74px',
                borderRadius: '8px',
                overflow: 'hidden',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                flexShrink: 0
              }}
            >
              <img 
                src={file.base64} 
                alt={file.name} 
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover'
                }}
              />
              <button
                onClick={() => setAttachments(prev => prev.filter(a => a.id !== file.id))}
                style={{
                  position: 'absolute',
                  top: '3px',
                  right: '3px',
                  width: '16px',
                  height: '16px',
                  borderRadius: '50%',
                  background: 'rgba(239, 68, 68, 0.85)',
                  color: 'white',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '9px',
                  fontWeight: 'bold',
                  lineHeight: 1,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={e => e.target.style.background = 'var(--accent-red)'}
                onMouseLeave={e => e.target.style.background = 'rgba(239, 68, 68, 0.85)'}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* DevOps Automation Toolkit */}
      {(() => {
        const isGithubActive = keys.GITHUB_TOKEN?.configured && keys.GITHUB_TOKEN?.enabled;
        const isVercelActive = keys.VERCEL_TOKEN?.configured && keys.VERCEL_TOKEN?.enabled && isGithubActive;
        const isRenderActive = keys.RENDER_TOKEN?.configured && keys.RENDER_TOKEN?.enabled && isGithubActive;

        const githubTooltip = !keys.GITHUB_TOKEN?.configured 
          ? "Enter API key to enable" 
          : !keys.GITHUB_TOKEN?.enabled 
            ? "Key is disabled in Settings" 
            : "";

        const vercelTooltip = !isGithubActive 
          ? "GitHub Key must be active to enable Vercel" 
          : !keys.VERCEL_TOKEN?.configured 
            ? "Enter API key to enable" 
            : !keys.VERCEL_TOKEN?.enabled 
              ? "Key is disabled in Settings" 
              : "";

        const renderTooltip = !isGithubActive 
          ? "GitHub Key must be active to enable Render" 
          : !keys.RENDER_TOKEN?.configured 
            ? "Enter API key to enable" 
            : !keys.RENDER_TOKEN?.enabled 
              ? "Key is disabled in Settings" 
              : "";

        return (
          <div className="devops-toolkit-panel">
            <div className="devops-toolkit-header">
              <div className="toolkit-header-left">
                <span className="toolkit-icon">🚀</span>
                <span className="toolkit-title">DevOps Automation Toolkit</span>
              </div>
              <div className="toolkit-status-indicator">
                {automationState.loading && (
                  <span className="toolkit-loading-text">
                    <span className="spinner-icon">⏳</span> Executing {automationState.type === 'folder' ? 'folder picker' : automationState.type === 'push' ? 'push to GitHub' : 'hosting deployment'}...
                  </span>
                )}
                {!automationState.loading && automationState.success && (
                  <span className="toolkit-success-text" title={automationState.success}>
                    ✅ {automationState.success.length > 50 ? automationState.success.substring(0, 50) + '...' : automationState.success}
                  </span>
                )}
                {!automationState.loading && automationState.error && (
                  <span className="toolkit-error-text" title={automationState.error}>
                    ⚠️ {automationState.error.length > 50 ? automationState.error.substring(0, 50) + '...' : automationState.error}
                  </span>
                )}
              </div>
            </div>

            <div className="devops-toolkit-body">
              <div className="devops-action-buttons">
                <div className="tooltip-container">
                  <button
                    className="devops-action-btn github-btn"
                    disabled={!isGithubActive || automationState.loading}
                    onClick={handlePushToGithub}
                  >
                    🐙 Push to GitHub
                  </button>
                  {githubTooltip && (
                    <span className="tooltip-text">{githubTooltip}</span>
                  )}
                </div>

                <div className="tooltip-container">
                  <button
                    className="devops-action-btn vercel-btn"
                    disabled={!isVercelActive || automationState.loading}
                    onClick={handleDeployToVercel}
                  >
                    ▲ Host with Vercel
                  </button>
                  {vercelTooltip && (
                    <span className="tooltip-text">{vercelTooltip}</span>
                  )}
                </div>

                <div className="tooltip-container">
                  <button
                    className="devops-action-btn render-btn"
                    disabled={!isRenderActive || automationState.loading}
                    onClick={handleDeployToRender}
                  >
                    ☁️ Host on Render
                  </button>
                  {renderTooltip && (
                    <span className="tooltip-text">{renderTooltip}</span>
                  )}
                </div>
              </div>

              <div className="devops-toolkit-configs">
                <div className="config-item" onClick={handleSelectFolder}>
                  <span className="config-label">📁 Folder:</span>
                  <span className="config-value" title={projectPath || "Click to select local folder"}>
                    {projectPath ? projectPath.split(/[\\/]/).pop() : "Select Folder..."}
                  </span>
                </div>

                <div className="config-item" onClick={() => {
                  setInputGithubUrl(githubUrl);
                  setShowLinkModal(true);
                }}>
                  <span className="config-label">🔗 Repo URL:</span>
                  <span className="config-value" title={githubUrl || "Click to link GitHub repository"}>
                    {githubUrl ? githubUrl.split('/').slice(-2).join('/') : "Link Repo..."}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* 🔗 Link GitHub URL Modal */}
      {showLinkModal && (
        <div className="modal-overlay" style={{ zIndex: 3000 }}>
          <div className="auth-modal" style={{ maxWidth: '440px', width: '90%', padding: '24px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '800', color: '#fff' }}>
              Link GitHub Repository
            </h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
              Enter the GitHub repository URL to configure target hosting deployments.
            </p>
            <form onSubmit={handleSaveGithubUrl} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <input
                type="url"
                placeholder="https://github.com/username/repo"
                value={inputGithubUrl}
                onChange={e => setInputGithubUrl(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-glass)',
                  background: 'rgba(0, 0, 0, 0.3)',
                  color: '#fff',
                  fontSize: '13px',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
                <button
                  type="button"
                  onClick={() => setShowLinkModal(false)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-glass)',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: 'none',
                    background: 'var(--gradient-accent)',
                    color: '#fff',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  Save URL
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 📁 Manual Folder Path Modal */}
      {showFolderModal && (
        <div className="modal-overlay" style={{ zIndex: 3000 }}>
          <div className="auth-modal" style={{ maxWidth: '440px', width: '90%', padding: '24px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '800', color: '#fff' }}>
              Enter Folder Path Manually
            </h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
              Provide the absolute file system path of your project folder.
            </p>
            <form onSubmit={handleSaveFolderPath} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <input
                type="text"
                placeholder="e.g. C:\Users\HP\DevOps-Project"
                value={inputFolderPath}
                onChange={e => setInputFolderPath(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-glass)',
                  background: 'rgba(0, 0, 0, 0.3)',
                  color: '#fff',
                  fontSize: '13px',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
                <button
                  type="button"
                  onClick={() => setShowFolderModal(false)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-glass)',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: 'none',
                    background: 'var(--gradient-accent)',
                    color: '#fff',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  Save Path
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="input-bar">

        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder="Describe what you want to build, deploy, or document..."
          rows={1}
          style={{ paddingRight: '92px' }} // Adjusted to fit both photo and send buttons
        />
        
        {/* 📷 ATTACHMENT PHOTO BUTTON */}
        <button
          className="attach-btn"
          onClick={handleCameraClick}
          style={{
            position: 'absolute',
            right: '48px',
            bottom: '8px',
            width: '36px',
            height: '36px',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-glass)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '16px',
            transition: 'all var(--transition-normal)',
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
          title="Attach photos"
        >
          📷
        </button>
        <input 
          type="file"
          accept="image/*"
          multiple
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        {state.isStreaming ? (
          <button
            className="send-btn"
            disabled
            style={{
              opacity: 0.4,
              cursor: 'not-allowed',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border-glass)',
              color: 'var(--text-muted)'
            }}
            title="Agent is executing..."
          >
            ⏳
          </button>
        ) : (
          <button
            className="send-btn"
            onClick={handleSubmit}
            disabled={!input.trim() && attachments.length === 0}
          >
            ▲
          </button>
        )}
      </div>
      {state.promptQueue.length > 0 && (
        <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'center' }}>
          <span className="queued-badge">
            ⏳ Queued Tasks: {state.promptQueue.length}
          </span>
        </div>
      )}

      {/* 📷 VISION Engine Setup Warning Overlay */}
      {showVisionWarning && (
        <div 
          className="modal-overlay" 
          style={{ 
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 3000, 
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(5, 7, 10, 0.85)',
            backdropFilter: 'blur(8px)',
            animation: 'fadeIn 0.2s ease-out'
          }}
        >
          <div 
            className="auth-modal" 
            style={{ 
              maxWidth: '460px', 
              width: '90%', 
              padding: '28px', 
              borderRadius: '16px',
              border: '1px solid var(--border-glass)',
              background: 'linear-gradient(135deg, rgba(20, 26, 35, 0.98) 0%, rgba(13, 17, 23, 0.98) 100%)',
              boxShadow: '0 10px 40px rgba(6, 182, 212, 0.12)',
              display: 'flex',
              flexDirection: 'column',
              gap: '18px',
              boxSizing: 'border-box',
              animation: 'scaleUp 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)'
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '32px' }}>📷</span>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#fff' }}>
                Vision Engine Required
              </h3>
            </div>

            {/* Message */}
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              To upload and analyze images, you need to enable an image-capable AI engine. Please select one of these two options:
            </p>

            {/* Options list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', margin: '8px 0' }}>
              {/* Option 1: Gemini */}
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-glass)', padding: '12px', borderRadius: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--accent-cyan)', display: 'block', marginBottom: '4px' }}>
                  Option A: Get a Free Gemini API Key (Cloud)
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4', display: 'block' }}>
                  Get a free key from <strong><a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-cyan)', textDecoration: 'underline' }}>Google AI Studio ↗</a></strong>, open the <strong>Settings panel (⚙️)</strong>, and save it under <strong>Primary Gemini API Key</strong>.
                </span>
              </div>

              {/* Option 2: Local Vision */}
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-glass)', padding: '12px', borderRadius: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--accent-green)', display: 'block', marginBottom: '4px' }}>
                  Option B: Install a Local Vision Model (Offline & Free)
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4', display: 'block' }}>
                  Open the <strong>Settings panel (⚙️)</strong> and install either <strong>Llava 7B</strong> or <strong>Llama 3.2 Vision 11B</strong> from the local model section to run 100% offline.
                </span>
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
              <button
                onClick={() => setShowVisionWarning(false)}
                style={{
                  padding: '8px 18px',
                  borderRadius: '8px',
                  border: 'none',
                  background: 'var(--gradient-accent)',
                  color: '#fff',
                  fontSize: '12px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  boxShadow: 'var(--shadow-glow)'
                }}
                onMouseEnter={e => e.currentTarget.style.opacity = '0.9'}
                onMouseLeave={e => e.currentTarget.style.opacity = '1'}
              >
                Got It
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
