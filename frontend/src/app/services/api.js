let base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
if (base.endsWith('/')) {
  base = base.slice(0, -1);
}
if (base.endsWith('/api')) {
  base = base.slice(0, -4);
}
export const API_BASE = base;

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error);
  }
  return res.json();
}

export async function fetchSessions(query) {
  const q = query ? `?q=${encodeURIComponent(query)}` : '';
  return request(`/api/chat/sessions${q}`);
}

export async function fetchHistory(sessionId) {
  return request(`/api/chat/history/${sessionId}`);
}

export async function deleteSession(sessionId) {
  return request(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function renameSession(sessionId, title) {
  return request(`/api/chat/sessions/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify({ title }),
  });
}

export async function fetchKeys() {
  return request('/api/settings/keys');
}

export async function saveKey(name, value) {
  return request('/api/settings/keys', {
    method: 'POST',
    body: JSON.stringify({ name, value }),
  });
}

export async function removeKey(name) {
  return request(`/api/settings/keys/${name}`, { method: 'DELETE' });
}

export async function fetchModels() {
  return request('/api/settings/models');
}

export async function addQueueKey(provider, label, value) {
  return request('/api/settings/keys/queue', {
    method: 'POST',
    body: JSON.stringify({ provider, label, value }),
  });
}

export async function removeQueueKey(keyId) {
  return request(`/api/settings/keys/queue/${keyId}`, { method: 'DELETE' });
}

export async function toggleKey(name) {
  return request(`/api/settings/keys/${name}/toggle`, { method: 'POST' });
}

export async function toggleQueueKey(keyId) {
  return request(`/api/settings/keys/queue/${keyId}/toggle`, { method: 'POST' });
}

export async function approveAction(actionId) {
  return request(`/api/auth/approve/${actionId}`, { method: 'POST' });
}

export async function denyAction(actionId) {
  return request(`/api/auth/deny/${actionId}`, { method: 'POST' });
}

export function streamChat(message, conversationId, model, userMemory, onEvent, images = null) {
  const controller = new AbortController();

  fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      model,
      user_memory: userMemory,
      images,
    }),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      const errorText = await response.text().catch(() => `HTTP ${response.status}`);
      onEvent({ type: 'error', content: `Server error (${response.status}): ${errorText}` });
      onEvent({ type: 'done' });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const convId = response.headers.get('X-Conversation-Id');
    if (convId) onEvent({ type: 'session_id', id: convId });

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);
          } catch {}
        }
      }
    }
    // Stream completed: ensure frontend resets the loading/thinking states
    onEvent({ type: 'done' });
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onEvent({ type: 'error', content: err.message });
      onEvent({ type: 'done' });
    }
  });

  return controller;
}

export async function pauseAgent(conversationId) {
  return request(`/api/chat/agent/${conversationId}/pause`, { method: 'POST' });
}

export async function resumeAgent(conversationId) {
  return request(`/api/chat/agent/${conversationId}/resume`, { method: 'POST' });
}

export async function stopAgent(conversationId) {
  return request(`/api/chat/agent/${conversationId}/stop`, { method: 'POST' });
}

export async function selectFolder() {
  return request('/api/settings/select-folder', { method: 'POST' });
}

export async function devopsPush(projectDir, repoName = null, isPrivate = false) {
  return request('/api/settings/devops/push', {
    method: 'POST',
    body: JSON.stringify({ project_dir: projectDir, repo_name: repoName, private: isPrivate }),
  });
}

export async function devopsDeployVercel(githubUrl, projectName = null) {
  return request('/api/settings/devops/deploy/vercel', {
    method: 'POST',
    body: JSON.stringify({ github_url: githubUrl, project_name: projectName }),
  });
}

export async function devopsDeployRender(githubUrl, projectName = null) {
  return request('/api/settings/devops/deploy/render', {
    method: 'POST',
    body: JSON.stringify({ github_url: githubUrl, project_name: projectName }),
  });
}


