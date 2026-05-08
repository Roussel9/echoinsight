export const dynamic = 'force-dynamic';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://backend:8000';

export async function POST(_request: Request, ctx: { params: { task_id: string } }) {
  const taskId = ctx.params.task_id;
  const res = await fetch(`${BACKEND_URL}/reprocess/${encodeURIComponent(taskId)}`, { method: 'POST' });

  const body = await res.text();
  return new Response(body, {
    status: res.status,
    headers: { 'content-type': res.headers.get('content-type') ?? 'application/json' },
  });
}

