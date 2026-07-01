const API_BASE = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  const res = await fetch(`${API_BASE}/api/settings/keys`);
  const data = await res.json();
  return Response.json(data);
}

export async function POST(request) {
  const body = await request.json();
  const res = await fetch(`${API_BASE}/api/settings/keys`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return Response.json(data);
}

export async function DELETE(request) {
  const { searchParams } = new URL(request.url);
  const name = searchParams.get('name');
  const res = await fetch(`${API_BASE}/api/settings/keys/${name}`, { method: 'DELETE' });
  const data = await res.json();
  return Response.json(data);
}
