import React, { useState } from "react";
import { 
  Play, 
  Database, 
  ArrowsClockwise, 
  Terminal, 
  ChartLineUp, 
  WarningCircle, 
  CheckCircle 
} from "@phosphor-icons/react";

interface LogEntry {
  id: string;
  timestamp: string;
  action: string;
  status: "running" | "success" | "error";
  output?: string;
}

export const ControlCenter: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const triggerAction = async (actionId: string, actionName: string) => {
    if (isRunning) return;
    
    setIsRunning(true);
    const logId = Math.random().toString(36).substring(7);
    const now = new Date().toLocaleTimeString();

    setLogs((prev) => [
      { id: logId, timestamp: now, action: actionName, status: "running" },
      ...prev.slice(0, 4)
    ]);

    try {
      const response = await fetch("http://localhost:4000/api/actions/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: actionId }),
      });

      const data = await response.json();

      setLogs((prev) =>
        prev.map((log) =>
          log.id === logId
            ? {
                ...log,
                status: data.success ? "success" : "error",
                output: data.output || data.error_output || data.error,
              }
            : log
        )
      );
    } catch (err: any) {
      setLogs((prev) =>
        prev.map((log) =>
          log.id === logId
            ? { ...log, status: "error", output: err.message }
            : log
        )
      );
    } finally {
      setIsRunning(false);
    }
  };

  const actions = [
    {
      id: "sync_today",
      name: "Sync Today's Data",
      description: "Run run_pipeline.py for today",
      icon: <Play weight="duotone" className="w-5 h-5" />,
      color: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    },
    {
      id: "recover_10d",
      name: "Recover Last 10 Days",
      description: "Run backfill.py",
      icon: <ArrowsClockwise weight="duotone" className="w-5 h-5" />,
      color: "text-blue-400 bg-blue-400/10 border-blue-400/20",
    },
    {
      id: "vif_audit",
      name: "Run VIF Audit",
      description: "Check multicollinearity (VIF > 10)",
      icon: <ChartLineUp weight="duotone" className="w-5 h-5" />,
      color: "text-purple-400 bg-purple-400/10 border-purple-400/20",
    },
    {
      id: "full_repopulation",
      name: "Full Repopulation (2016)",
      description: "Run backfill_all.py (Heavy)",
      icon: <Database weight="duotone" className="w-5 h-5" />,
      color: "text-orange-400 bg-orange-400/10 border-orange-400/20",
    },
  ];

  return (
    <div className="flex flex-col gap-4 bg-[#0a0a0f] p-6 rounded-3xl border border-[#202025]/50 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl">
      <div>
        <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-gray-500">
          Developer Tools
        </span>
        <h3 className="text-sm font-semibold text-[#f3f4f6] mt-0.5">Control Center</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
        {actions.map((act) => (
          <button
            key={act.id}
            onClick={() => triggerAction(act.id, act.name)}
            disabled={isRunning}
            className={`flex items-start gap-3 p-3 text-left rounded-xl border border-[#202025] bg-[#050505] transition-all
              ${isRunning ? "opacity-50 cursor-not-allowed" : "hover:border-gray-700 hover:bg-[#111] active:scale-[0.98]"}`}
          >
            <div className={`p-2 rounded-lg border ${act.color}`}>
              {act.icon}
            </div>
            <div>
              <div className="text-xs font-semibold text-gray-200">{act.name}</div>
              <div className="text-[10px] text-gray-500 mt-0.5">{act.description}</div>
            </div>
          </button>
        ))}
      </div>

      {logs.length > 0 && (
        <div className="mt-4 border border-[#202025] rounded-xl bg-[#050505] overflow-hidden flex flex-col">
          <div className="bg-[#111] px-4 py-2 border-b border-[#202025] flex items-center gap-2">
            <Terminal className="w-4 h-4 text-gray-400" />
            <span className="text-xs font-mono text-gray-400 uppercase tracking-widest">Execution Log</span>
          </div>
          <div className="p-4 flex flex-col gap-3 max-h-[200px] overflow-y-auto custom-scrollbar">
            {logs.map((log) => (
              <div key={log.id} className="flex flex-col gap-1.5 border-b border-[#202025]/50 pb-3 last:border-0 last:pb-0">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-gray-600 font-mono">{log.timestamp}</span>
                  <span className="text-gray-300 font-medium">{log.action}</span>
                  {log.status === "running" && (
                    <span className="ml-auto text-yellow-500 flex items-center gap-1">
                      <ArrowsClockwise className="w-3.5 h-3.5 animate-spin" /> Running
                    </span>
                  )}
                  {log.status === "success" && (
                    <span className="ml-auto text-emerald-500 flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5" /> Success
                    </span>
                  )}
                  {log.status === "error" && (
                    <span className="ml-auto text-rose-500 flex items-center gap-1">
                      <WarningCircle className="w-3.5 h-3.5" /> Failed
                    </span>
                  )}
                </div>
                {log.output && (
                  <pre className="text-[10px] font-mono text-gray-400 bg-[#0a0a0f] p-2 rounded border border-[#202025] overflow-x-auto whitespace-pre-wrap">
                    {log.output}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
