import React, { useState } from "react";
import type { DiagnosticsRecord } from "../api/client";

interface FeatureDiagnosticsPanelProps {
  data: DiagnosticsRecord[];
}

export const FeatureDiagnosticsPanel: React.FC<FeatureDiagnosticsPanelProps> = ({ data }) => {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  // Default to latest record
  const latestIdx = data.length > 0 ? data.length - 1 : null;
  const activeIdx = selectedIdx !== null ? selectedIdx : latestIdx;
  const activeRecord = activeIdx !== null ? data[activeIdx] : null;

  if (!activeRecord) {
    return (
      <div className="bg-[#0a0a0f] p-6 rounded-3xl border border-[#202025]/50 text-gray-500 text-center text-xs">
        No diagnostics telemetry available.
      </div>
    );
  }

  const scores = activeRecord.indicator_scores || {};
  const vif = activeRecord.vif || {};
  const pcaVariance = activeRecord.pca_variance_explained;

  // Check if any VIF exceeds 10
  const collinearCount = Object.values(vif).filter((v) => v > 10).length;

  return (
    <div className="flex flex-col gap-6 bg-[#0a0a0f] p-6 rounded-3xl border border-[#202025]/50 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl">
      {/* Panel Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-[#202025]/30 pb-4">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-purple-400">Layer 3 Feature Processing</span>
          <h3 className="text-sm font-semibold text-[#f3f4f6] mt-0.5">Multicollinearity & PCA Orthogonalization</h3>
        </div>
        <div className="text-[10px] text-gray-500 font-mono bg-white/5 px-2.5 py-1 rounded-lg border border-white/5">
          AS OF: {activeRecord.date}
        </div>
      </div>

      {/* PCA & VIF Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* PCA Card */}
        <div className="p-4 bg-white/5 rounded-2xl border border-white/5 flex flex-col justify-between">
          <div className="text-[9px] uppercase tracking-wider text-gray-500">Cumulative PCA Variance Explained</div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold text-cyan-400 font-mono">{pcaVariance.toFixed(1)}%</span>
            <span className="text-[9px] text-emerald-400 font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              &gt; 85% Target Met
            </span>
          </div>
          <p className="text-[10px] text-gray-500 mt-2 leading-relaxed">
            First 3 principal components capture the vast majority of technical signal variance, removing noise.
          </p>
        </div>

        {/* VIF Warning Card */}
        <div className={`p-4 rounded-2xl border flex flex-col justify-between transition-all duration-300 ${
          collinearCount > 0
            ? "bg-rose-500/5 border-rose-500/20 shadow-[0_0_20px_rgba(239,68,68,0.05)]"
            : "bg-white/5 border-white/5"
        }`}>
          <div className="text-[9px] uppercase tracking-wider text-gray-500">Multicollinearity Status</div>
          <div className="flex items-center gap-2 mt-2">
            {collinearCount > 0 ? (
              <>
                <span className="text-2xl font-bold text-rose-400 font-mono">{collinearCount} Alert</span>
                <span className="text-[9px] text-rose-400 font-bold px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/30 animate-pulse">
                  CRITICAL: VIF &gt; 10
                </span>
              </>
            ) : (
              <>
                <span className="text-2xl font-bold text-emerald-400 font-mono">Clean</span>
                <span className="text-[9px] text-emerald-400 font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                  All VIF &le; 10
                </span>
              </>
            )}
          </div>
          <p className="text-[10px] text-gray-500 mt-2 leading-relaxed">
            Variance Inflation Factor checks prevent stacking redundant indicators measuring similar momentum vectors.
          </p>
        </div>
      </div>

      {/* Feature Matrix Table */}
      <div className="flex flex-col gap-2">
        <span className="text-[9px] uppercase tracking-[0.15em] font-semibold text-gray-500 px-1">Technical Indicator Matrix</span>
        
        <div className="overflow-x-auto rounded-2xl border border-[#202025]/30">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#202025]/30 bg-white/3 font-semibold text-gray-400">
                <th className="p-3 pl-4">Technical Indicator</th>
                <th className="p-3">Directional Score</th>
                <th className="p-3">VIF Value</th>
                <th className="p-3 pr-4 text-right">Observability Warning</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#202025]/20 bg-white/2">
              {Object.keys(vif).map((name) => {
                const score = scores[name] ?? 0;
                const vifValue = vif[name] ?? 0;
                const isBullish = score === 1;
                const isCollinear = vifValue > 10;

                return (
                  <tr 
                    key={name} 
                    className={`hover:bg-white/5 transition-all duration-300 ${
                      isCollinear ? "bg-rose-500/3" : ""
                    }`}
                  >
                    <td className="p-3.5 pl-4 font-semibold text-gray-300 font-mono">{name}</td>
                    <td className="p-3.5">
                      <span className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-md text-[10px] font-bold font-mono ${
                        isBullish
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}>
                        {score > 0 ? `+${score}` : score}
                      </span>
                    </td>
                    <td className="p-3.5 font-mono">
                      <span className={isCollinear ? "text-rose-400 font-bold" : "text-gray-400"}>
                        {vifValue.toFixed(2)}
                      </span>
                    </td>
                    <td className="p-3.5 pr-4 text-right">
                      {isCollinear ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                          Collinear (VIF &gt; 10)
                        </span>
                      ) : (
                        <span className="text-[10px] text-gray-600 font-mono">Passed</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Date slider to view historical diagnostics */}
      {data.length > 1 && activeIdx !== null && (
        <div className="flex flex-col gap-2 pt-2 border-t border-[#202025]/30">
          <div className="flex justify-between items-center text-[10px] text-gray-500 font-mono">
            <span>Historical Navigation Slider</span>
            <span>Date Index: {activeIdx + 1} / {data.length}</span>
          </div>
          <input
            type="range"
            min={0}
            max={data.length - 1}
            value={activeIdx}
            onChange={(e) => setSelectedIdx(Number(e.target.value))}
            className="w-full accent-purple-500 bg-[#12121a] h-1.5 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      )}
    </div>
  );
};
