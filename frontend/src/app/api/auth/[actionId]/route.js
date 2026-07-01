const API_BASE = process.env.BACKEND_URL || 'http://localhost:8000';

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
