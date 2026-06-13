import React, { useMemo } from "react";
import type { ChartRecord } from "../api/client";

interface TradingLogPanelProps {
  data: ChartRecord[];
}

export const TradingLogPanel: React.FC<TradingLogPanelProps> = ({ data }) => {
  const trades = useMemo(() => {
    if (!data || data.length === 0) return [];

    const logs: any[] = [];
    let prevExposure = 0;
    let entryPrice = 0;
    let entryDate = "";

    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));

    sortedData.forEach((r) => {
      const exposure = r.target_exposure ?? 0;
      
      if (exposure > 0 && prevExposure === 0) {
        // BUY signal generated today. Execution usually happens on next open, but we use today's close as proxy
        entryPrice = r.close ?? 0;
        entryDate = r.date;
      } else if (exposure === 0 && prevExposure > 0) {
        // SELL signal
        const exitPrice = r.close ?? 0;
        const pnl = entryPrice > 0 ? ((exitPrice - entryPrice) / entryPrice) * 100 : 0;
        
        logs.push({
          entryDate,
          exitDate: r.date,
          entryPrice,
          exitPrice,
          pnl,
        });
      }
      
      prevExposure = exposure;
    });

    return logs.reverse(); // Latest first
  }, [data]);

  if (trades.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--color-text-muted)] text-sm">
        No completed trades yet.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto w-full h-full pr-2">
      <table className="w-full text-left border-collapse">
        <thead className="sticky top-0 bg-[var(--color-canvas)] z-10">
          <tr className="border-b border-[var(--color-border)] text-[var(--color-text-muted)] text-xs font-medium uppercase tracking-wider">
            <th className="pb-3 pl-2">Entry Date</th>
            <th className="pb-3">Exit Date</th>
            <th className="pb-3 text-right">Entry Price</th>
            <th className="pb-3 text-right">Exit Price</th>
            <th className="pb-3 pr-2 text-right">Trade PnL</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border)] text-sm">
          {trades.map((t, i) => (
            <tr key={i} className="hover:bg-[var(--color-surface-hover)] transition-colors">
              <td className="py-3 pl-2 font-[var(--font-mono)] text-[var(--color-text-primary)]">{t.entryDate}</td>
              <td className="py-3 font-[var(--font-mono)] text-[var(--color-text-muted)]">{t.exitDate}</td>
              <td className="py-3 text-right font-[var(--font-mono)]">${t.entryPrice.toFixed(2)}</td>
              <td className="py-3 text-right font-[var(--font-mono)]">${t.exitPrice.toFixed(2)}</td>
              <td className={`py-3 pr-2 text-right font-[var(--font-mono)] font-bold ${t.pnl >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]"}`}>
                {t.pnl >= 0 ? "+" : ""}{t.pnl.toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
