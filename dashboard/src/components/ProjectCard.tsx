interface Container {
  Name: string;
  Service: string;
  State: string;
  Status: string;
  Health?: string;
}

interface Props {
  name: string;
  containers: Container[];
  onDeploy: () => void;
  onLogs: (container: string) => void;
}

function StateDot({ state }: { state: string }) {
  const color =
    state === "running"
      ? "bg-green-400"
      : state === "restarting"
      ? "bg-yellow-400 animate-pulse"
      : "bg-red-500";
  return <span className={`inline-block w-2 h-2 rounded-full ${color} shrink-0 mt-0.5`} />;
}

export default function ProjectCard({ name, containers, onDeploy, onLogs }: Props) {
  const allUp = containers.length > 0 && containers.every((c) => c.State === "running");
  const anyDown = containers.some((c) => c.State !== "running");

  const headerColor = containers.length === 0
    ? "text-gray-500"
    : allUp
    ? "text-green-400"
    : anyDown
    ? "text-red-400"
    : "text-yellow-400";

  return (
    <div className="bg-[#111] border border-[#222] rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className={`font-bold text-sm tracking-wide ${headerColor}`}>{name}</h2>
        <span className="text-xs text-gray-600">
          {containers.length === 0 ? "no containers" : `${containers.filter((c) => c.State === "running").length}/${containers.length} up`}
        </span>
      </div>

      <div className="flex flex-col gap-1.5 min-h-[2rem]">
        {containers.length === 0 ? (
          <span className="text-xs text-gray-600">—</span>
        ) : (
          containers.map((c) => (
            <div key={c.Name} className="flex items-start gap-2">
              <StateDot state={c.State} />
              <div className="flex flex-col min-w-0">
                <span className="text-xs text-gray-300 truncate">{c.Service || c.Name}</span>
                <span className="text-xs text-gray-600 truncate">{c.Status}</span>
              </div>
              <button
                onClick={() => onLogs(c.Name)}
                className="ml-auto text-xs text-gray-500 hover:text-gray-300 shrink-0 px-1"
                title="logs"
              >
                logs
              </button>
            </div>
          ))
        )}
      </div>

      <button
        onClick={onDeploy}
        className="w-full bg-[#1a1a1a] hover:bg-[#222] border border-[#333] hover:border-green-600 text-green-400 text-xs font-bold py-1.5 rounded transition-colors"
      >
        deploy
      </button>
    </div>
  );
}
