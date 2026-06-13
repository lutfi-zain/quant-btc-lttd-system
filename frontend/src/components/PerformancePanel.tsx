import React, { useMemo } from "react";
import type { ChartRecord } from "../api/client";

interface PerformancePanelProps {
  data: ChartRecord[];
}

export const PerformancePanel: React.FC<PerformancePanelProps> = ({ data }) => {
  const metrics = useMemo(() => {
    if (!data || data.length === 0) return null;

    let equity = 1.0;
    let btcHold = 1.0;
    let peakEquity = 1.0;
    let maxDrawdown = 0;
    
    let prevExposure = 0;
    const dailyReturns: number[] = [];
    
    let winTrades = 0;
    let totalTrades = 0;
    let currentTradeReturn = 0;
    let inTrade = false;

    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));

    sortedData.forEach((r, i) => {
      if (i > 0) {
        const prevR = sortedData[i - 1];
        if (prevR.close && r.close) {
          const btcDailyReturn = (r.close - prevR.close) / prevR.close;
          btcHold = btcHold * (1 + btcDailyReturn);
          
          const stratReturn = prevExposure * btcDailyReturn;
          equity = equity * (1 + stratReturn);
          dailyReturns.push(stratReturn);

          if (equity > peakEquity) peakEquity = equity;
          const drawdown = (peakEquity - equity) / peakEquity;
          if (drawdown > maxDrawdown) maxDrawdown = drawdown;

          if (inTrade) {
            currentTradeReturn = (1 + currentTradeReturn) * (1 + stratReturn) - 1;
          }
        }
      }

      const exposure = r.target_exposure ?? 0;
      if (exposure > 0 && prevExposure === 0) {
        inTrade = true;
        currentTradeReturn = 0;
        totalTrades++;
      } else if (exposure === 0 && prevExposure > 0) {
        inTrade = false;
        if (currentTradeReturn > 0) winTrades++;
      }

      prevExposure = exposure;
    });

    const days = dailyReturns.length;
    const years = days / 365.25;
    
    const totalReturnPct = (equity - 1) * 100;
    const btcReturnPct = (btcHold - 1) * 100;
    
    const cagr = (Math.pow(equity, 1 / (years || 1)) - 1) * 100;
    const btcCagr = (Math.pow(btcHold, 1 / (years || 1)) - 1) * 100;

    const meanDailyReturn = dailyReturns.reduce((a, b) => a + b, 0) / (days || 1);
    const variance = dailyReturns.reduce((a, b) => a + Math.pow(b - meanDailyReturn, 2), 0) / (days || 1);
    const stdDev = Math.sqrt(variance);
    const annualizedStdDev = stdDev * Math.sqrt(365);
    
    // Risk-free rate assumed 0 for simplicity
    const sharpe = annualizedStdDev > 0 ? (meanDailyReturn * 365) / annualizedStdDev : 0;

    return {
      totalReturnPct,
      btcReturnPct,
      cagr,
      btcCagr,
      maxDrawdown: maxDrawdown * 100,
      sharpe,
      winRate: totalTrades > 0 ? (winTrades / totalTrades) * 100 : 0,
      totalTrades,
    };
  }, [data]);

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--color-text-muted)] text-sm">
        No performance data available.
      </div>
    );
  }

  const outperforming = metrics.totalReturnPct > metrics.btcReturnPct;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 p-2 h-full content-center">
      <MetricBox label="Strategy Return" value={`+${metrics.totalReturnPct.toFixed(2)}%`} color={outperforming ? "var(--color-bull)" : "var(--color-text-primary)"} />
      <MetricBox label="Buy & Hold Return" value={`+${metrics.btcReturnPct.toFixed(2)}%`} color="var(--color-text-muted)" />
      
      <MetricBox label="Strategy CAGR" value={`${metrics.cagr.toFixed(2)}%`} />
      <MetricBox label="Buy & Hold CAGR" value={`${metrics.btcCagr.toFixed(2)}%`} color="var(--color-text-muted)" />
      
      <MetricBox label="Max Drawdown" value={`-${metrics.maxDrawdown.toFixed(2)}%`} color="var(--color-bear)" />
      <MetricBox label="Sharpe Ratio" value={metrics.sharpe.toFixed(2)} />
      
      <MetricBox label="Win Rate" value={`${metrics.winRate.toFixed(1)}%`} />
      <MetricBox label="Total Trades" value={metrics.totalTrades.toString()} />
    </div>
  );
};

const MetricBox = ({ label, value, color }: { label: string; value: string; color?: string }) => (
  <div className="flex flex-col gap-1">
    <span className="text-[10px] uppercase tracking-wider font-medium text-[var(--color-text-muted)]">{label}</span>
    <span className="text-2xl font-[var(--font-mono)]" style={{ color: color || "var(--color-text-primary)" }}>{value}</span>
  </div>
);
