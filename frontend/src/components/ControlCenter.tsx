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
      icon: <Play weight="bold" className="w-5 h-5" />,
      color: "text-[var(--color-bull)] bg-[var(--color-surface)] border-[var(--color-border)]",
    },
    {
      id: "recover_10d",
      name: "Recover Last 10 Days",
      description: "Run backfill.py",
      icon: <ArrowsClockwise weight="bold" className="w-5 h-5" />,
      color: "text-[#1F6C9F] bg-[#E1F3FE] border-[var(--color-border)]",
    },
    {
      id: "vif_audit",
      name: "Run VIF Audit",
      description: "Check multicollinearity (VIF > 10)",
      icon: <ChartLineUp weight="bold" className="w-5 h-5" />,
      color: "text-[#5B3E96] bg-[#F1EDF9] border-[var(--color-border)]",
    },
    {
      id: "full_repopulation",
      name: "Full Repopulation",
      description: "Run backfill_all.py (Heavy)",
      icon: <Database weight="bold" className="w-5 h-5" />,
      color: "text-[var(--color-bear)] bg-[var(--color-surface)] border-[var(--color-border)]",
    },
  ];

  return (
    <div className="flex flex-col gap-4 h-full">

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
        {actions.map((act) => (
          <button
            key={act.id}
            onClick={() => triggerAction(act.id, act.name)}
            disabled={isRunning}
            className={`flex items-start gap-3 p-3 text-left rounded border border-[var(--color-border)] bg-[var(--color-surface)] transition-all shadow-sm
              ${isRunning ? "opacity-50 cursor-not-allowed" : "hover:bg-[var(--color-surface)] active:scale-[0.98]"}`}
          >
            <div className={`p-2 rounded border ${act.color}`}>
              {act.icon}
            </div>
            <div>
              <div className="text-sm font-medium text-[var(--color-text-primary)]">{act.name}</div>
              <div className="text-[10px] font-mono text-[var(--color-text-muted)] mt-0.5">{act.description}</div>
            </div>
          </button>
        ))}
      </div>

      {logs.length > 0 && (
        <div className="mt-4 border border-[var(--color-border)] rounded bg-[var(--color-surface)] shadow-sm overflow-hidden flex flex-col">
          <div className="bg-[var(--color-surface)] px-4 py-2 border-b border-[var(--color-border)] flex items-center gap-2">
            <Terminal className="w-4 h-4 text-[var(--color-text-muted)]" />
            <span className="text-[10px] font-mono text-[var(--color-text-muted)] uppercase tracking-[0.1em]">Execution Log</span>
          </div>
          <div className="p-4 flex flex-col gap-3 max-h-[200px] overflow-y-auto custom-scrollbar">
            {logs.map((log) => (
              <div key={log.id} className="flex flex-col gap-1.5 border-b border-[var(--color-border)] pb-3 last:border-0 last:pb-0">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-[var(--color-text-muted)] font-mono text-[10px]">{log.timestamp}</span>
                  <span className="text-[var(--color-text-primary)] font-mono text-[10px]">{log.action}</span>
                  {log.status === "running" && (
                    <span className="ml-auto text-[var(--color-sideways)] flex items-center gap-1 font-mono text-[10px] bg-[var(--color-surface)] px-1.5 rounded">
                      <ArrowsClockwise className="w-3.5 h-3.5 animate-spin" /> Running
                    </span>
                  )}
                  {log.status === "success" && (
                    <span className="ml-auto text-[var(--color-bull)] flex items-center gap-1 font-mono text-[10px] bg-[var(--color-surface)] px-1.5 rounded">
                      <CheckCircle className="w-3.5 h-3.5" /> Success
                    </span>
                  )}
                  {log.status === "error" && (
                    <span className="ml-auto text-[var(--color-bear)] flex items-center gap-1 font-mono text-[10px] bg-[var(--color-surface)] px-1.5 rounded">
                      <WarningCircle className="w-3.5 h-3.5" /> Failed
                    </span>
                  )}
                </div>
                {log.output && (
                  <pre className="text-[10px] font-mono text-[var(--color-text-muted)] bg-[var(--color-surface)] p-2 rounded border border-[var(--color-border)] overflow-x-auto whitespace-pre-wrap">
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
