import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchLatestLTTD, fetchLTTDHistory, fetchHealthStatus } from "../api/client";
import type { Regime } from "../api/client";
import { TradingViewChart } from "./TradingViewChart";

export const Dashboard: React.FC = () => {
  // Query backend health
  const { data: health, isError: isHealthError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealthStatus,
    refetchInterval: 10000, // Check health every 10s
  });

  // Query latest LTTD evaluation
  const {
    data: latest,
    isLoading: isLatestLoading,
    isError: isLatestError,
    refetch: refetchLatest,
  } = useQuery({
    queryKey: ["latestLTTD"],
    queryFn: fetchLatestLTTD,
    refetchInterval: 30000, // Check for updates every 30s
  });

  // Query historical LTTD evaluations
  const {
    data: history,
    isLoading: isHistoryLoading,
    isError: isHistoryError,
    refetch: refetchHistory,
  } = useQuery({
    queryKey: ["lttdHistory"],
    queryFn: () => fetchLTTDHistory(), // Fetch all historical data
  });

  // Calculate regime transitions in-memory from history
  const transitions = useMemo(() => {
    if (!history || history.length < 2) return [];
    const logs: Array<{
      date: string;
      prev: Regime;
      next: Regime;
      score: number;
    }> = [];
    
    for (let i = 1; i < history.length; i++) {
      if (history[i].regime !== history[i - 1].regime) {
        logs.push({
          date: history[i].date,
          prev: history[i - 1].regime,
          next: history[i].regime,
          score: history[i].final_score,
        });
      }
    }
    // Return latest transitions first
    return logs.reverse();
  }, [history]);

  const handleRefresh = () => {
    refetchLatest();
    refetchHistory();
  };

  const isServerOffline = isHealthError || (health && !health.status);

  if (isLatestLoading || isHistoryLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#030303] text-gray-400">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-4 border-purple-500/10 border-t-purple-500 animate-spin"></div>
        </div>
        <p className="mt-4 text-xs tracking-widest uppercase text-purple-400/80 animate-pulse">
          Loading Quantitative Telemetry...
        </p>
      </div>
    );
  }

  if (isLatestError || isHistoryError || isServerOffline) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#030303] p-6 text-center">
        <div className="p-1.5 bg-red-500/10 rounded-full border border-red-500/20 mb-4 animate-bounce">
          <div className="p-3 bg-red-500/20 rounded-full">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
        </div>
        <h2 className="text-xl font-bold text-gray-200 tracking-tight">Hono API Server Unreachable</h2>
        <p className="text-sm text-gray-500 mt-2 max-w-md">
          The quantitative database status check failed or returned an offline status. Please verify Bun/Hono server execution on port 3000.
        </p>
        <button
          onClick={handleRefresh}
          className="mt-6 px-6 py-2.5 rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-semibold border border-red-500/20 transition-all duration-300 active:scale-[0.98]"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const currentRegime = latest?.regime || "SIDEWAYS";
  const finalScore = latest?.final_score ?? 0;
  const targetExposure = latest?.target_exposure ?? 0;

  // Regime styling settings
  const regimeMeta = {
    BULL: {
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
      glow: "shadow-[0_0_50px_rgba(16,185,129,0.15)]",
      desc: "Uptrend momentum detected. Long exposure active.",
    },
    BEAR: {
      color: "text-rose-400",
      bg: "bg-rose-500/10",
      border: "border-rose-500/20",
      glow: "shadow-[0_0_50px_rgba(239,68,68,0.15)]",
      desc: "Downtrend bias confirmed. Exposure forced to cash.",
    },
    SIDEWAYS: {
      color: "text-purple-400",
      bg: "bg-purple-500/10",
      border: "border-purple-500/20",
      glow: "shadow-[0_0_50px_rgba(168,85,247,0.15)]",
      desc: "Mean reversion active. Sizing exposure strictly capped.",
    },
  }[currentRegime];

  return (
    <div className="min-h-screen bg-[#030303] text-gray-300 font-sans selection:bg-purple-500/30 selection:text-purple-200">
      
      {/* Background Mesh Gradients */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className={`absolute top-[-10%] left-[20%] w-[600px] h-[600px] rounded-full filter blur-[150px] opacity-20 transition-all duration-1000 ${
          currentRegime === "BULL" ? "bg-emerald-500" : currentRegime === "BEAR" ? "bg-rose-500" : "bg-purple-500"
        }`}></div>
        <div className="absolute bottom-[10%] right-[10%] w-[500px] h-[500px] rounded-full bg-blue-600/10 filter blur-[130px] pointer-events-none"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-12 flex flex-col gap-10">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 pb-6 border-b border-[#202025]/30">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-gray-400">System Live</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#f3f4f6] tracking-tight mt-3">
              LTTD <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">Quantitative Portal</span>
            </h1>
            <p className="text-xs text-gray-500 mt-1.5">
              Macro Directional Trend & Ornstein-Uhlenbeck Regime Telemetry
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-[10px] uppercase tracking-wider text-gray-500">Last Synced</div>
              <div className="text-xs font-semibold text-gray-300 font-mono mt-0.5">{latest?.date}</div>
            </div>
            <button
              onClick={handleRefresh}
              className="p-3 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 text-gray-400 hover:text-white transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] active:scale-[0.95]"
              title="Refresh Data"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.253 8H18" />
              </svg>
            </button>
          </div>
        </header>

        {/* Row 1: Dashboard Bento Cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Card A: Regime Widget */}
          <div className={`group p-0.5 bg-[#15151e]/30 rounded-3xl border border-[#23232f]/30 hover:border-white/10 transition-all duration-500 ${regimeMeta.glow}`}>
            <div className="p-6 bg-[#08080f]/90 rounded-[calc(1.5rem-0.125rem)] flex flex-col h-full justify-between shadow-[inset_0_1px_1px_rgba(255,255,255,0.03)]">
              <div>
                <span className="text-[9px] uppercase tracking-[0.2em] font-semibold text-gray-500">HMM Layer 1 Inference</span>
                <h3 className="text-lg font-bold text-gray-200 tracking-tight mt-1">Market Regime</h3>
              </div>
              <div className="my-8 flex flex-col items-center">
                <div className={`text-4xl font-black tracking-wider ${regimeMeta.color} animate-pulse`}>
                  {currentRegime}
                </div>
                <div className={`mt-3 text-[11px] font-medium px-3.5 py-1 rounded-full ${regimeMeta.bg} ${regimeMeta.color} border ${regimeMeta.border}`}>
                  Posterior Prob: {latest?.posterior_prob ? `${(latest.posterior_prob * 100).toFixed(1)}%` : "N/A"}
                </div>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed text-center">
                {regimeMeta.desc}
              </p>
            </div>
          </div>

          {/* Card B: Final Score Widget */}
          <div className="group p-0.5 bg-[#15151e]/30 rounded-3xl border border-[#23232f]/30 hover:border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.2)] transition-all duration-500">
            <div className="p-6 bg-[#08080f]/90 rounded-[calc(1.5rem-0.125rem)] flex flex-col h-full justify-between shadow-[inset_0_1px_1px_rgba(255,255,255,0.03)]">
              <div>
                <span className="text-[9px] uppercase tracking-[0.2em] font-semibold text-gray-500">Lasso Layer 4 Ensemble</span>
                <h3 className="text-lg font-bold text-gray-200 tracking-tight mt-1">LTTD Final Score</h3>
              </div>
              <div className="my-6 flex flex-col items-center">
                <div className="text-5xl font-black tracking-tight text-[#f3f4f6] font-mono">
                  {finalScore > 0 ? `+${finalScore.toFixed(4)}` : finalScore.toFixed(4)}
                </div>
                
                {/* Horizontal meter */}
                <div className="w-full bg-white/5 h-1.5 rounded-full mt-6 overflow-hidden border border-white/5 relative">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full transition-all duration-700 ease-out"
                    style={{ width: `${((finalScore + 1) / 2) * 100}%` }}
                  />
                  <div className="absolute top-0 bottom-0 w-0.5 bg-white/20 left-1/2" /> {/* Center mark */}
                </div>
                <div className="flex justify-between w-full text-[9px] text-gray-600 mt-2 font-mono">
                  <span>-1.0 (Bearish)</span>
                  <span>0.0</span>
                  <span>+1.0 (Bullish)</span>
                </div>
              </div>
              <div className="flex justify-between items-center px-2 py-1.5 bg-white/5 rounded-2xl border border-white/5">
                <span className="text-[10px] text-gray-500 font-medium uppercase tracking-wide">Target Exposure</span>
                <span className="text-xs font-bold text-indigo-400 font-mono">{(targetExposure * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          {/* Card C: Diagnostic / Metadata Widget */}
          <div className="group p-0.5 bg-[#15151e]/30 rounded-3xl border border-[#23232f]/30 hover:border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.2)] transition-all duration-500">
            <div className="p-6 bg-[#08080f]/90 rounded-[calc(1.5rem-0.125rem)] flex flex-col h-full justify-between shadow-[inset_0_1px_1px_rgba(255,255,255,0.03)]">
              <div>
                <span className="text-[9px] uppercase tracking-[0.2em] font-semibold text-gray-500">Infrastructure Layer 6</span>
                <h3 className="text-lg font-bold text-gray-200 tracking-tight mt-1">Telemetry Status</h3>
              </div>
              <div className="my-4 flex flex-col gap-3">
                <div className="flex justify-between items-center py-2 border-b border-[#202025]/30">
                  <span className="text-xs text-gray-500">Database Status</span>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span className="w-1 h-1 rounded-full bg-emerald-400"></span>
                    WAL Active
                  </span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-[#202025]/30">
                  <span className="text-xs text-gray-500">Ingest Freshness</span>
                  <span className="text-xs font-semibold text-gray-300 font-mono">Fresh</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-xs text-gray-500">Trailing Epoch context</span>
                  <span className="text-xs font-semibold text-gray-300 font-mono">1,200 Days</span>
                </div>
              </div>
              <div className="text-[10px] text-gray-600 bg-white/5 px-3 py-2 rounded-xl border border-white/5 font-mono break-all text-center">
                DB: lttd.db
              </div>
            </div>
          </div>

        </section>

        {/* Row 2: Charts and Indicator Telemetry */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Main Chart Column (span 8) */}
          <div className="lg:col-span-8 flex flex-col h-full">
            <TradingViewChart data={history || []} />
          </div>

          {/* Indicator Scores Column (span 4) */}
          <div className="lg:col-span-4 p-0.5 bg-[#15151e]/30 rounded-3xl border border-[#23232f]/30 hover:border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.2)]">
            <div className="p-6 bg-[#08080f]/90 rounded-[calc(1.5rem-0.125rem)] flex flex-col h-full justify-between shadow-[inset_0_1px_1px_rgba(255,255,255,0.03)]">
              <div>
                <span className="text-[9px] uppercase tracking-[0.2em] font-semibold text-gray-500">Layer 2 Auditing</span>
                <h3 className="text-lg font-bold text-gray-200 tracking-tight mt-1">Causal Indicator Scores</h3>
                
                <div className="mt-4 flex flex-col gap-2 max-h-[420px] overflow-y-auto pr-1">
                  
                  {latest?.indicator_scores && Object.keys(latest.indicator_scores).length > 0 ? (
                    Object.entries(latest.indicator_scores).map(([name, score]) => {
                      const isBullish = score === 1;
                      return (
                        <div 
                          key={name} 
                          className="flex justify-between items-center p-2.5 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-all duration-300"
                        >
                          <span className="text-xs font-semibold text-gray-300 font-mono">{name}</span>
                          <span className={`inline-flex items-center justify-center w-8 py-0.5 rounded-md text-[10px] font-bold font-mono ${
                            isBullish 
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          }`}>
                            {score > 0 ? `+${score}` : score}
                          </span>
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-xs text-gray-600 text-center py-6">
                      No active indicator telemetry recorded.
                    </div>
                  )}

                </div>
              </div>

              <div className="text-[10px] text-gray-600 text-center border-t border-[#202025]/30 pt-4 mt-4 leading-relaxed font-mono">
                Scores ∈ &#123;-1, +1&#125; represent daily directional outputs.
              </div>
            </div>
          </div>

        </section>

        {/* Row 3: Regime Shift Notifications */}
        <section className="grid grid-cols-1 gap-6">
          
          <div className="p-0.5 bg-[#15151e]/30 rounded-3xl border border-[#23232f]/30 hover:border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.2)]">
            <div className="p-6 bg-[#08080f]/90 rounded-[calc(1.5rem-0.125rem)] shadow-[inset_0_1px_1px_rgba(255,255,255,0.03)]">
              <span className="text-[9px] uppercase tracking-[0.2em] font-semibold text-gray-500">System Logs</span>
              <h3 className="text-lg font-bold text-gray-200 tracking-tight mt-1 mb-6">Regime Transition Log</h3>
              
              <div className="overflow-y-auto max-h-[400px] overflow-x-auto pr-2 scrollbar-thin scrollbar-thumb-white/10">
                <table className="w-full text-left border-collapse">
                  <thead className="sticky top-0 bg-[#08080f] z-10 shadow-[inset_0_-1px_0_rgba(255,255,255,0.05)]">
                    <tr className="border-b border-[#202025]/40 text-gray-500 text-[10px] uppercase tracking-wider font-semibold">
                      <th className="pb-3 pl-2 bg-[#08080f]">Transition Date</th>
                      <th className="pb-3 bg-[#08080f]">Previous Regime</th>
                      <th className="pb-3 bg-[#08080f]">New Inferred Regime</th>
                      <th className="pb-3 bg-[#08080f]">Ensemble Score</th>
                      <th className="pb-3 pr-2 text-right bg-[#08080f]">Observability Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#202025]/30 text-xs">
                    {transitions.length > 0 ? (
                      transitions.map((t, idx) => (
                        <tr key={idx} className="hover:bg-white/5 transition-all duration-300">
                          <td className="py-3.5 pl-2 font-semibold text-gray-300 font-mono">{t.date}</td>
                          <td className="py-3.5">
                            <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-gray-400">
                              {t.prev}
                            </span>
                          </td>
                          <td className="py-3.5">
                            <span className={`px-2.5 py-0.5 rounded-full font-bold border ${
                              t.next === "BULL" 
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                                : t.next === "BEAR"
                                ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                : "bg-purple-500/10 text-purple-400 border-purple-500/20"
                            }`}>
                              {t.next}
                            </span>
                          </td>
                          <td className="py-3.5 font-mono text-gray-400">
                            {t.score > 0 ? `+${t.score.toFixed(4)}` : t.score.toFixed(4)}
                          </td>
                          <td className="py-3.5 pr-2 text-right text-gray-500 font-mono">
                            ✓ Recorded
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-gray-600">
                          No historical regime transitions detected.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

        </section>

      </div>
    </div>
  );
};
export default Dashboard;
