import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const form = await request.formData();
  const password = form.get("password") as string;

  if (password !== process.env.DASHBOARD_PASSWORD) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set("jarvis_auth", process.env.DASHBOARD_TOKEN!, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30,
    path: "/",
  });
  return response;
}
