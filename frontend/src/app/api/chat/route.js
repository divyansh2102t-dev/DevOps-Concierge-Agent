const API_BASE = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request) {
  const body = await request.json();

  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const stream = response.body;
  const convId = response.headers.get('X-Conversation-Id');

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Conversation-Id': convId || '',
    },
  });
}
