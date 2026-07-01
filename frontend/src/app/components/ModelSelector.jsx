'use client';
import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { fetchModels } from '../services/api';

export default function ModelSelector() {
  const { state, dispatch } = useApp();
  const [models, setModels] = useState([
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
    { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
    { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro ✨' },
  ]);

  useEffect(() => {
    async function loadModels() {
      try {
        const list = await fetchModels();
        if (list && list.length > 0) {
          setModels(list);
        }
      } catch (err) {
        console.error('Failed to fetch models:', err);
      }
    }
    loadModels();
    
    // Periodically refresh list to detect newly installed Ollama models
    const interval = setInterval(loadModels, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="model-selector">
      <select
        value={state.model}
        onChange={e => dispatch({ type: 'SET_MODEL', payload: e.target.value })}
      >
        {models.map(m => (
          <option key={m.id} value={m.id} disabled={m.available === false}>
            {m.name || m.label || m.id} {m.available === false ? '(Unavailable)' : ''}
          </option>
        ))}
      </select>
    </div>
  );
}
