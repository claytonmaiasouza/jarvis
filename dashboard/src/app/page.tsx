"use client";

import { useCallback, useEffect, useState } from "react";
import MetricsBar from "@/components/MetricsBar";
import ProjectCard from "@/components/ProjectCard";
import StreamModal from "@/components/StreamModal";

interface Container {
  Name: string;
  Service: string;
  State: string;
  Status: string;
  Health?: string;
}

interface Metrics {
  cpu_pct: number;
  mem_pct: number;
  mem_used_mb: number;
  mem_total_mb: number;
  disk_pct: number;
  disk_used_gb: number;
  disk_total_gb: number;
}

interface Modal {
  title: string;
  url: string;
  method: "GET" | "POST";
}

const PROJECT_ORDER = [
  "agendamento",
  "bot-restaurante",
  "farmacia-santaclara",
  "fintrack",
  "jarvis",
];

export default function Dashboard() {
  const [status, setStatus] = useState<Record<string, Container[]>>({});
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [modal, setModal] = useState<Modal | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, m] = await Promise.all([
        fetch("/api/status").then((r) => r.json()),
        fetch("/api/metrics").then((r) => r.json()),
      ]);
      setStatus(s);
      setMetrics(m);
      setLastUpdated(new Date());
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30_000);
    return () => clearInterval(id);
  }, [refresh]);

  const projects = PROJECT_ORDER.filter((p) => p in status).concat(
    Object.keys(status).filter((p) => !PROJECT_ORDER.includes(p))
  );

  return (
    <main className="min-h-screen p-6 max-w-6xl mx-auto">
      <header className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold tracking-widest text-green-400">JARVIS</h1>
          <button
            onClick={refresh}
            className="text-xs text-gray-600 hover:text-gray-300 transition-colors"
            title="refresh"
          >
            ↻
          </button>
          {error && <span className="text-xs text-red-400">worker unreachable</span>}
          {lastUpdated && !error && (
            <span className="text-xs text-gray-600">
              {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <MetricsBar metrics={metrics} />
      </header>

      {projects.length === 0 ? (
        <div className="text-gray-600 text-sm">loading...</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((name) => (
            <ProjectCard
              key={name}
              name={name}
              containers={status[name] ?? []}
              onDeploy={() =>
                setModal({
                  title: `deploy · ${name}`,
                  url: `/api/deploy/${name}`,
                  method: "POST",
                })
              }
              onLogs={(container) =>
                setModal({
                  title: `logs · ${container}`,
                  url: `/api/logs/${container}`,
                  method: "GET",
                })
              }
            />
          ))}
        </div>
      )}

      {modal && (
        <StreamModal
          title={modal.title}
          url={modal.url}
          method={modal.method}
          onClose={() => {
            setModal(null);
            refresh();
          }}
        />
      )}
    </main>
  );
}
