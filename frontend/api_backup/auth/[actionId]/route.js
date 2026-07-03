let base = process.env.BACKEND_URL || 'http://localhost:8000';
if (base.endsWith('/')) {
  base = base.slice(0, -1);
}
if (base.endsWith('/api')) {
  base = base.slice(0, -4);
}
const API_BASE = base;

export async function POST(request, { params }) {
  const { actionId } = await params;
  const { searchParams } = new URL(request.url);
  const action = searchParams.get('action') || 'approve';

  const res = await fetch(`${API_BASE}/api/auth/${action}/${actionId}`, {
    method: 'POST',
  });
  const data = await res.json();
  return Response.json(data);
}
