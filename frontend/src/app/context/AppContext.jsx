'use client';
import { createContext, useContext, useReducer, useCallback, useEffect } from 'react';

const AppContext = createContext(null);

const initialState = {
  sessions: [],
  currentSessionId: 'single_session',
  messages: { 'single_session': [] },
  promptQueue: [], // Queue of prompts waiting to be executed: [{ id, content, dependsOn }]
  settingsOpen: false,
  historyOpen: false, // Tracks if conversation history panel is open
  sidebarOpen: false, // Sidebar starts closed / not used
  model: 'gemini-2.5-flash',
  authRequest: null,
  activeAgents: [],
  keys: {},
  isStreaming: false,
  retryMessage: null,
  terminals: [],
  terminalOpen: false,
  agentState: null, // 'running', 'paused', 'stopped', or null
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_TERMINALS':
      return { ...state, terminals: action.payload };
    case 'TOGGLE_TERMINAL':
      return { ...state, terminalOpen: !state.terminalOpen };
    case 'SET_TERMINAL_OPEN':
      return { ...state, terminalOpen: action.payload };
    case 'SET_SESSIONS':
      return { ...state, sessions: action.payload };
    case 'SET_CURRENT_SESSION':
      return { ...state, currentSessionId: 'single_session' };
    case 'SET_MESSAGES':
      return { ...state, messages: { ...state.messages, [action.sessionId]: action.payload } };
    case 'ADD_MESSAGE': {
      const sessionMsgs = state.messages[action.sessionId] || [];
      return { ...state, messages: { ...state.messages, [action.sessionId]: [...sessionMsgs, action.payload] } };
    }
    case 'UPDATE_LAST_MESSAGE': {
      const msgs = [...(state.messages[action.sessionId] || [])];
      if (msgs.length > 0) {
        const last = { ...msgs[msgs.length - 1] };
        last.content = (last.content || '') + action.payload;
        msgs[msgs.length - 1] = last;
      }
      return { ...state, messages: { ...state.messages, [action.sessionId]: msgs } };
    }
    case 'UPDATE_MESSAGE_BY_ID': {
      const msgs = [...(state.messages[action.sessionId] || [])];
      const idx = msgs.findIndex(m => m.id === action.messageId);
      if (idx >= 0) {
        msgs[idx] = { ...msgs[idx], content: (msgs[idx].content || '') + action.payload };
      }
      return { ...state, messages: { ...state.messages, [action.sessionId]: msgs } };
    }
    case 'UPDATE_MESSAGE_PROPS': {
      const msgs = [...(state.messages[action.sessionId] || [])];
      const idx = msgs.findIndex(m => m.id === action.messageId);
      if (idx >= 0) {
        msgs[idx] = { ...msgs[idx], ...action.payload };
      }
      return { ...state, messages: { ...state.messages, [action.sessionId]: msgs } };
    }
    case 'ADD_TO_QUEUE':
      return { ...state, promptQueue: [...state.promptQueue, action.payload] };
    case 'DEQUEUE':
      return { ...state, promptQueue: state.promptQueue.slice(1) };
    case 'TOGGLE_SETTINGS':
      return { ...state, settingsOpen: !state.settingsOpen };
    case 'OPEN_SETTINGS':
      return { ...state, settingsOpen: true };
    case 'CLOSE_SETTINGS':
      return { ...state, settingsOpen: false };
    case 'TOGGLE_HISTORY':
      return { ...state, historyOpen: !state.historyOpen };
    case 'CLOSE_HISTORY':
      return { ...state, historyOpen: false };
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen };
    case 'SET_MODEL':
      return { ...state, model: action.payload };
    case 'SET_AUTH_REQUEST':
      return { ...state, authRequest: action.payload };
    case 'CLEAR_AUTH_REQUEST':
      return { ...state, authRequest: null };
    case 'SET_ACTIVE_AGENTS':
      return { ...state, activeAgents: action.payload };
    case 'ADD_AGENT':
      return { ...state, activeAgents: [...state.activeAgents, action.payload] };
    case 'REMOVE_AGENT':
      return { ...state, activeAgents: state.activeAgents.filter(a => a.id !== action.payload) };
    case 'SET_KEYS':
      return { ...state, keys: action.payload };
    case 'SET_STREAMING':
      return { ...state, isStreaming: action.payload };
    case 'ADD_TOOL_CARD': {
      const toolMsgs = [...(state.messages[action.sessionId] || [])];
      toolMsgs.push({ role: 'tool', ...action.payload });
      return { ...state, messages: { ...state.messages, [action.sessionId]: toolMsgs } };
    }
    case 'UPDATE_TOOL_CARD': {
      const tMsgs = [...(state.messages[action.sessionId] || [])];
      // Update by messageId if present, or fallback to finding by toolName
      const idx = action.payload.messageId 
        ? tMsgs.findIndex(m => m.role === 'tool' && m.id === action.payload.messageId)
        : tMsgs.findIndex(m => m.role === 'tool' && m.toolName === action.payload.toolName && m.status !== 'done');
      if (idx >= 0) {
        tMsgs[idx] = { ...tMsgs[idx], ...action.payload };
      }
      return { ...state, messages: { ...state.messages, [action.sessionId]: tMsgs } };
    }
    case 'CLEAR_NEW_MESSAGES': {
      const { __new__, ...rest } = state.messages;
      return { ...state, messages: rest };
    }
    case 'REMOVE_LAST_ASSISTANT': {
      const rMsgs = [...(state.messages[action.sessionId] || [])];
      for (let i = rMsgs.length - 1; i >= 0; i--) {
        if (rMsgs[i].role === 'assistant' || rMsgs[i].role === 'tool') {
          rMsgs.splice(i, 1);
        } else {
          break;
        }
      }
      return { ...state, messages: { ...state.messages, [action.sessionId]: rMsgs } };
    }
    case 'SET_RETRY':
      return { ...state, retryMessage: action.payload };
    case 'CLEAR_RETRY':
      return { ...state, retryMessage: null };
    case 'SET_AGENT_STATE':
      return { ...state, agentState: action.payload };
    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Sync with localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('devops_concierge_chat_history');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          dispatch({ type: 'SET_MESSAGES', sessionId: 'single_session', payload: parsed });
        } catch (e) {
          console.error('Failed to parse chat history from localStorage', e);
        }
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined' && state.messages['single_session']) {
      localStorage.setItem('devops_concierge_chat_history', JSON.stringify(state.messages['single_session']));
    }
  }, [state.messages['single_session']]);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
}
