"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  title: string;
  url: string;
  method?: "GET" | "POST";
  onClose: () => void;
}

export default function StreamModal({ title, url, method = "GET", onClose }: Props) {
  const [lines, setLines] = useState<string[]>([]);
  const [done, setDone] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);

  useEffect(() => {
    setLines([]);
    setDone(false);

    let cancelled = false;

    async function stream() {
      try {
        const res = await fetch(url, { method });
        if (!res.body) return;
        const reader = res.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done: streamDone, value } = await reader.read();
          if (streamDone || cancelled) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            if (part.startsWith("data: ")) {
              const line = part.slice(6);
              if (!cancelled) setLines((prev) => [...prev, line]);
            }
          }
        }
      } catch {
        // closed by user
      } finally {
        if (!cancelled) setDone(true);
      }
    }

    stream();

    return () => {
      cancelled = true;
      readerRef.current?.cancel();
    };
  }, [url, method]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg w-full max-w-2xl mx-4 flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a]">
          <span className="text-sm font-bold text-green-400">{title}</span>
          <div className="flex items-center gap-3">
            {!done && (
              <span className="text-xs text-yellow-400 animate-pulse">running...</span>
            )}
            {done && <span className="text-xs text-green-400">done</span>}
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-200 text-lg leading-none"
            >
              ×
            </button>
          </div>
        </div>

        <div className="overflow-y-auto flex-1 p-4 text-xs text-gray-300 leading-relaxed">
          {lines.map((line, i) => (
            <div key={i} className={line.startsWith("$") ? "text-green-400 mt-2" : line.includes("✓") ? "text-green-300 font-bold" : line.toLowerCase().includes("error") ? "text-red-400" : ""}>
              {line || " "}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
