interface Metrics {
  cpu_pct: number;
  mem_pct: number;
  mem_used_mb: number;
  mem_total_mb: number;
  disk_pct: number;
  disk_used_gb: number;
  disk_total_gb: number;
}

function Bar({ label, pct, detail }: { label: string; pct: number; detail: string }) {
  const color =
    pct > 85 ? "bg-red-500" : pct > 65 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400 w-10 shrink-0">{label}</span>
      <div className="w-20 h-1.5 bg-[#222] rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-gray-300 whitespace-nowrap">{detail}</span>
    </div>
  );
}

export default function MetricsBar({ metrics }: { metrics: Metrics | null }) {
  if (!metrics) {
    return <div className="text-xs text-gray-600">loading metrics...</div>;
  }
  return (
    <div className="flex flex-col gap-1.5">
      <Bar label="CPU" pct={metrics.cpu_pct} detail={`${metrics.cpu_pct}%`} />
      <Bar
        label="RAM"
        pct={metrics.mem_pct}
        detail={`${metrics.mem_used_mb}/${metrics.mem_total_mb} MB`}
      />
      <Bar
        label="DISK"
        pct={metrics.disk_pct}
        detail={`${metrics.disk_used_gb}/${metrics.disk_total_gb} GB`}
      />
    </div>
  );
}
