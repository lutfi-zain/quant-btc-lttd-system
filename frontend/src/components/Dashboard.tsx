import React, { useMemo, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchLatestLTTD,
  fetchLTTDHistory,
  fetchHealthStatus,
  fetchChartData,
  fetchRegimeData,
  fetchDiagnosticsData,
  fetchOnChainData,
  triggerAction,
} from "../api/client";
import { SynchronizedChartProvider } from "./SynchronizedChartContext";
import { LTTDChart } from "./LTTDChart";
import { RegimePanel } from "./RegimePanel";
import { FeatureDiagnosticsPanel } from "./FeatureDiagnosticsPanel";
import { OnChainPanel } from "./OnChainPanel";
import { PerformancePanel } from "./PerformancePanel";
import { TradingLogPanel } from "./TradingLogPanel";

export const Dashboard: React.FC = () => {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [isTriggering, setIsTriggering] = useState(false);

  const [selectedAction, setSelectedAction] = useState("sync_today");

  useEffect(() => {
    // Check saved theme or system preference
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      setTheme("dark");
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    if (newTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const { data: health, isError: isHealthError } = useQuery({ queryKey: ["health"], queryFn: () => fetchHealthStatus(), refetchInterval: 10000 });
  const { data: latest, isLoading: isLatestLoading, isError: isLatestError, refetch: refetchLatest } = useQuery({ queryKey: ["latestLTTD"], queryFn: () => fetchLatestLTTD(), refetchInterval: 30000 });
  const { data: history, isLoading: isHistoryLoading, isError: isHistoryError, refetch: refetchHistory } = useQuery({ queryKey: ["lttdHistory"], queryFn: () => fetchLTTDHistory() });
  const { data: chartData, isLoading: isChartLoading, refetch: refetchChart } = useQuery({ queryKey: ["chartData"], queryFn: () => fetchChartData() });
  const { data: regimeData, isLoading: isRegimeLoading, refetch: refetchRegime } = useQuery({ queryKey: ["regimeData"], queryFn: () => fetchRegimeData() });
  const { data: diagnosticsData, isLoading: isDiagnosticsLoading, refetch: refetchDiagnostics } = useQuery({ queryKey: ["diagnosticsData"], queryFn: () => fetchDiagnosticsData() });
  const { data: onChainData, isLoading: isOnChainLoading, refetch: refetchOnChain } = useQuery({ queryKey: ["onChainData"], queryFn: () => fetchOnChainData() });

  const transitions = useMemo(() => {
    if (!history || history.length < 2) return [];
    const logs: any[] = [];
    for (let i = 1; i < history.length; i++) {
      if (history[i].regime !== history[i - 1].regime) {
        logs.push({ date: history[i].date, prev: history[i - 1].regime, next: history[i].regime, score: history[i].final_score });
      }
    }
    return logs.reverse();
  }, [history]);

  const handleRefresh = () => { refetchLatest(); refetchHistory(); refetchChart(); refetchRegime(); refetchDiagnostics(); refetchOnChain(); };

  const handleTriggerFetch = async () => {
    if (isTriggering) return;
    
    if (selectedAction === "reset_db" && !window.confirm("Are you sure you want to completely RESET the database? This cannot be undone.")) return;
    if (selectedAction === "full_repopulation" && !window.confirm("Full repopulation will take a long time. Proceed?")) return;

    setIsTriggering(true);
    try {
      await triggerAction(selectedAction);
      handleRefresh(); // Refresh UI after fetching data
      alert(`Action '${selectedAction}' completed successfully.`);
    } catch (err) {
      console.error("Failed to run action:", err);
      alert(`Failed to run action '${selectedAction}'.`);
    } finally {
      setIsTriggering(false);
    }
  };

  const isServerOffline = isHealthError || (health && !health.status);
  const isGlobalLoading = isLatestLoading || isHistoryLoading || isChartLoading || isRegimeLoading || isDiagnosticsLoading || isOnChainLoading;

  if (isGlobalLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-canvas)] text-[var(--color-text-primary)]">
        <div className="text-sm font-medium animate-pulse text-[var(--color-text-muted)]">Loading interface...</div>
      </div>
    );
  }

  if (isLatestError || isHistoryError || isServerOffline) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-canvas)] text-[var(--color-bear)] px-6 text-center">
        <h2 className="text-2xl font-[var(--font-display)] mb-2">Connection Error</h2>
        <p className="text-sm text-[var(--color-text-muted)] max-w-md mb-6">Unable to connect to the quantitative backend on port 4000.</p>
        <button onClick={handleRefresh} className="px-6 py-2 bg-[var(--color-accent)] text-[var(--color-canvas)] rounded-md text-sm">Retry Connection</button>
      </div>
    );
  }

  const currentRegime = latest?.regime || "SIDEWAYS";
  const finalScore = latest?.final_score ?? 0;
  const targetExposure = latest?.target_exposure ?? 0;

  const latestRegimeRecord = regimeData && regimeData.length > 0 ? regimeData[regimeData.length - 1] : null;
  const posteriorProb = latestRegimeRecord 
    ? (currentRegime === "BULL" ? latestRegimeRecord.p_bull 
       : currentRegime === "BEAR" ? latestRegimeRecord.p_bear 
       : latestRegimeRecord.p_sideways)
    : 0;

  const getRegimeBg = (regime: string) => {
    if (regime === 'BULL') return 'bg-[var(--color-bg-bull)] text-[var(--color-bull)]';
    if (regime === 'BEAR') return 'bg-[var(--color-bg-bear)] text-[var(--color-bear)]';
    return 'bg-[var(--color-bg-sideways)] text-[var(--color-sideways)]';
  };

  return (
     <div className="min-h-screen bg-[var(--color-canvas)] text-[var(--color-text-primary)] font-[var(--font-sans)] pb-24 transition-colors duration-300">
        
        {/* Editorial Header */}
        <header className="max-w-6xl mx-auto px-6 pt-16 pb-12 flex flex-col md:flex-row justify-between items-start md:items-end gap-6 animate-fade-up">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] mb-6 shadow-sm">
              <span className={`w-2 h-2 rounded-full ${isServerOffline ? 'bg-[var(--color-bear)]' : 'bg-[var(--color-bull)]'}`}></span>
              <span className="text-xs font-medium tracking-wide text-[var(--color-text-muted)] uppercase">System Active</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-[var(--font-display)] tracking-tight text-[var(--color-text-primary)] mb-3">
              LTTD Quant Dashboard
            </h1>
            <p className="text-[var(--color-text-muted)] text-sm max-w-lg leading-relaxed">
              Monitoring Bitcoin's long-term trend direction via Hidden Markov Models and Walk-Forward Optimization.
            </p>
          </div>
          
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-3">
              <button 
                onClick={toggleTheme}
                className="px-3 py-1 text-xs font-medium bg-[var(--color-surface)] border border-[var(--color-border)] rounded shadow-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors cursor-pointer"
              >
                {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
              </button>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Last Sync: <span className="font-[var(--font-mono)] text-[var(--color-text-primary)]">{latest?.date}</span></span>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <button 
                onClick={handleRefresh} 
                className="text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors underline underline-offset-4 decoration-[var(--color-border)] hover:decoration-[var(--color-text-primary)] cursor-pointer mr-2"
              >
                Refresh UI
              </button>
              <div className="flex items-center shadow-sm">
                <select
                  value={selectedAction}
                  onChange={(e) => setSelectedAction(e.target.value)}
                  className="px-2 py-1.5 text-xs font-medium bg-[var(--color-surface)] border border-r-0 border-[var(--color-border)] rounded-l text-[var(--color-text-primary)] focus:outline-none cursor-pointer"
                  disabled={isTriggering}
                >
                  <option value="sync_today">Sync Today</option>
                  <option value="recover_10d">Recover 10d</option>
                  <option value="full_repopulation">Full Backfill</option>
                  <option value="vif_audit">VIF Audit</option>
                  <option value="reset_db">Reset DB</option>
                </select>
                <button 
                  onClick={handleTriggerFetch} 
                  disabled={isTriggering}
                  className="px-3 py-1.5 bg-[var(--color-text-primary)] text-[var(--color-canvas)] border border-[var(--color-text-primary)] rounded-r text-xs font-medium hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isTriggering ? 'Running...' : 'Run'}
                </button>
              </div>
            </div>
          </div>
        </header>

        <div className="max-w-6xl mx-auto px-6">
          <SynchronizedChartProvider>
            <div className="bento-grid">
              
              {/* Macro Indicators Row */}
              <div className="col-span-12 md:col-span-4 minimalist-card flex flex-col justify-between animate-fade-up" style={{ animationDelay: '100ms' }}>
                 <div>
                   <span className="text-xs text-[var(--color-text-muted)] font-medium uppercase tracking-wider">Current Regime</span>
                   <div className="mt-4 flex items-center justify-between">
                     <div className={`text-4xl font-[var(--font-display)] tracking-tight ${getRegimeBg(currentRegime).split(' ')[1]}`}>
                       {currentRegime}
                     </div>
                     <div className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide ${getRegimeBg(currentRegime)}`}>
                       {(posteriorProb * 100).toFixed(1)}% PROB
                     </div>
                   </div>
                 </div>
                 <div className="mt-8 pt-4 border-t border-[var(--color-border)] text-sm text-[var(--color-text-muted)]">
                   HMM Layer 1 Classification
                 </div>
              </div>

              <div className="col-span-12 md:col-span-4 minimalist-card flex flex-col justify-between animate-fade-up" style={{ animationDelay: '150ms' }}>
                 <div>
                   <span className="text-xs text-[var(--color-text-muted)] font-medium uppercase tracking-wider">Ensemble Score</span>
                   <div className="mt-4 flex items-center justify-between">
                     <div className="text-4xl font-[var(--font-mono)] tracking-tight">
                       {finalScore > 0 ? `+${finalScore.toFixed(4)}` : finalScore.toFixed(4)}
                     </div>
                   </div>
                 </div>
                 <div className="mt-8 pt-4 border-t border-[var(--color-border)] text-sm text-[var(--color-text-muted)]">
                   PCA-Orthogonalized Aggregation
                 </div>
              </div>

              <div className="col-span-12 md:col-span-4 minimalist-card flex flex-col justify-between animate-fade-up" style={{ animationDelay: '200ms' }}>
                 <div>
                   <span className="text-xs text-[var(--color-text-muted)] font-medium uppercase tracking-wider">Target Exposure</span>
                   <div className="mt-4 flex items-center justify-between">
                     <div className="text-4xl font-[var(--font-display)] tracking-tight">
                       {(targetExposure * 100).toFixed(0)}%
                     </div>
                     <div className="px-3 py-1 rounded-full text-xs font-bold tracking-wide bg-[#F7F6F3] text-[var(--color-text-primary)] border border-[var(--color-border)]">
                       ALLOCATION
                     </div>
                   </div>
                 </div>
                 <div className="mt-8 pt-4 border-t border-[var(--color-border)] text-sm text-[var(--color-text-muted)]">
                   Suggested Portfolio Weight
                 </div>
              </div>

              {/* Performance Metrics Row */}
              <div className="col-span-12 minimalist-card flex flex-col animate-fade-up" style={{ animationDelay: '225ms' }}>
                 <div className="mb-4">
                   <h2 className="text-lg font-[var(--font-display)]">System Performance</h2>
                 </div>
                 <div className="w-full">
                    <PerformancePanel data={chartData || []} />
                 </div>
              </div>

              {/* Main Chart Row - Stable Height */}
              <div className="col-span-12 minimalist-card flex flex-col animate-fade-up" style={{ animationDelay: '250ms' }}>
                 <div className="mb-6 flex justify-between items-center">
                   <h2 className="text-lg font-[var(--font-display)]">Price Action, LTTD Score, Exposure & Equity</h2>
                   <span className="text-xs text-[var(--color-text-muted)] font-[var(--font-mono)]">BTC/USD (Daily)</span>
                 </div>
                 {/* Fixed/Stable Height Container */}
                 <div className="w-full h-[750px]">
                    <LTTDChart data={chartData || []} />
                 </div>
              </div>

              {/* Diagnostics Row */}
              <div className="col-span-12 md:col-span-6 minimalist-card flex flex-col animate-fade-up" style={{ animationDelay: '300ms' }}>
                 <div className="mb-6">
                   <h2 className="text-lg font-[var(--font-display)]">On-Chain Indicators</h2>
                 </div>
                 <div className="flex-1 h-[300px]">
                    <OnChainPanel data={onChainData || []} />
                 </div>
              </div>

              <div className="col-span-12 md:col-span-6 minimalist-card flex flex-col animate-fade-up" style={{ animationDelay: '350ms' }}>
                 <div className="mb-6">
                   <h2 className="text-lg font-[var(--font-display)]">Feature Diagnostics</h2>
                 </div>
                 <div className="flex-1 h-[300px] overflow-y-auto hidden-scrollbar">
                    <FeatureDiagnosticsPanel data={diagnosticsData || []} />
                 </div>
              </div>

              {/* Regime Probability Row */}
              <div className="col-span-12 minimalist-card flex flex-col animate-fade-up" style={{ animationDelay: '375ms' }}>
                 <div className="mb-6 flex justify-between items-center">
                   <h2 className="text-lg font-[var(--font-display)]">Regime Probability History</h2>
                 </div>
                 <div className="w-full h-[300px]">
                    <RegimePanel data={regimeData || []} />
                 </div>
              </div>

              {/* Audit Logs Row */}
              <div className="col-span-12 md:col-span-6 minimalist-card animate-fade-up" style={{ animationDelay: '400ms' }}>
                <div className="mb-6">
                  <h2 className="text-lg font-[var(--font-display)]">Regime Transition Audit</h2>
                </div>
                <div className="overflow-x-auto h-[350px] overflow-y-auto hidden-scrollbar">
                  <table className="w-full text-left border-collapse">
                    <thead className="sticky top-0 bg-[var(--color-canvas)] z-10">
                      <tr className="border-b border-[var(--color-border)] text-[var(--color-text-muted)] text-xs font-medium uppercase tracking-wider">
                        <th className="pb-3 pl-2">Date</th>
                        <th className="pb-3">Shift</th>
                        <th className="pb-3 pr-2 text-right">Score at Transition</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)] text-sm">
                      {transitions.map((t, i) => (
                          <tr key={i} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                            <td className="py-3 pl-2 font-[var(--font-mono)] text-[var(--color-text-muted)]">{t.date}</td>
                            <td className="py-3">
                              <span className="font-medium text-[var(--color-text-primary)]">{t.prev}</span>
                              <span className="mx-2 text-[var(--color-text-muted)]">→</span>
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide ${getRegimeBg(t.next)}`}>
                                {t.next}
                              </span>
                            </td>
                            <td className="py-3 pr-2 text-right font-[var(--font-mono)]">{t.score > 0 ? `+${t.score.toFixed(4)}` : t.score.toFixed(4)}</td>
                          </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Trading Log Row */}
              <div className="col-span-12 md:col-span-6 minimalist-card animate-fade-up" style={{ animationDelay: '425ms' }}>
                <div className="mb-6">
                  <h2 className="text-lg font-[var(--font-display)]">Trading Log</h2>
                </div>
                <div className="h-[350px] overflow-y-auto hidden-scrollbar">
                  <TradingLogPanel data={chartData || []} />
                </div>
              </div>

            </div>
          </SynchronizedChartProvider>
        </div>
     </div>
  );
};
export default Dashboard;
