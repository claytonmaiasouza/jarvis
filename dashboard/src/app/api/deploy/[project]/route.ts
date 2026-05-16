export const dynamic = "force-dynamic";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ project: string }> }
) {
  const { project } = await params;
  const upstream = await fetch(
    `${process.env.WORKER_URL}/deploy/stream/${project}`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.WORKER_API_KEY}` },
    }
  );

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
