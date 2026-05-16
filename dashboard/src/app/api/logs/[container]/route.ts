export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ container: string }> }
) {
  const { container } = await params;
  const upstream = await fetch(
    `${process.env.WORKER_URL}/logs/stream/${container}`,
    {
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
