"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

function LoginForm() {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const params = useSearchParams();
  const error = params.get("error");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const form = new FormData();
    form.append("password", password);
    const res = await fetch("/api/auth", { method: "POST", body: form });
    if (res.ok || res.redirected) {
      router.push("/");
    } else {
      router.push("/login?error=1");
    }
    setLoading(false);
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a]">
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-4 w-72"
      >
        <h1 className="text-2xl font-bold tracking-widest text-green-400 text-center">
          JARVIS
        </h1>
        {error && (
          <p className="text-red-400 text-sm text-center">senha incorreta</p>
        )}
        <input
          type="password"
          placeholder="senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="bg-[#111] border border-[#333] rounded px-3 py-2 text-sm focus:outline-none focus:border-green-500"
          autoFocus
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-green-600 hover:bg-green-500 disabled:opacity-50 text-black font-bold py-2 rounded text-sm transition-colors"
        >
          {loading ? "..." : "entrar"}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
