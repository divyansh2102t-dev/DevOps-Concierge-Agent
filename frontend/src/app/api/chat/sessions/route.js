const API_BASE = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q');
  const url = q
    ? `${API_BASE}/api/chat/sessions?q=${encodeURIComponent(q)}`
    : `${API_BASE}/api/chat/sessions`;

  const res = await fetch(url);
  const data = await res.json();
  return Response.json(data);
}
