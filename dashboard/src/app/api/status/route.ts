export const dynamic = "force-dynamic";

export async function GET() {
  const res = await fetch(`${process.env.WORKER_URL}/status`, {
    headers: { Authorization: `Bearer ${process.env.WORKER_API_KEY}` },
    cache: "no-store",
  });
  const data = await res.json();
  return Response.json(data);
}
