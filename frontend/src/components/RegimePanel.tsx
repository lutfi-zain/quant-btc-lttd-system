/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/exhaustive-deps */
import React, { useEffect, useRef, useState } from "react";
import { createChart, AreaSeries } from "lightweight-charts";
import type { IChartApi } from "lightweight-charts";
import { useSynchronizedCharts } from "./SynchronizedChartContext";
import type { RegimeRecord } from "../api/client";

interface RegimePanelProps {
  data: RegimeRecord[];
}

export const RegimePanel: React.FC<RegimePanelProps> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [hoveredData, setHoveredData] = useState<RegimeRecord | null>(null);
  const { registerChart, unregisterChart, registerSeries, syncCrosshair, syncTimeScale } = useSynchronizedCharts();

  const chartId = "regime-panel";

  // Get latest state as default
  const latestState = data.length > 0 ? data[data.length - 1] : null;
  const activeState = hoveredData || latestState;

  // Determine dominant regime
  const dominantRegime = activeState
    ? activeState.p_bull > 0.5
      ? "BULL"
      : activeState.p_bear > 0.5
      ? "BEAR"
      : activeState.p_sideways > 0.5
      ? "SIDEWAYS"
      : null
    : null;

  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && containerRef.current) {
        chartRef.current.resize(containerRef.current.clientWidth, 220);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const themeColors = {
      bg: "#050505",
      grid: "#111115",
      text: "#8a8f98",
      border: "#202025",
      bull: "rgba(16, 185, 129, 0.4)",      // Emerald green
      bear: "rgba(239, 68, 68, 0.4)",        // Rose red
      sideways: "rgba(168, 85, 247, 0.4)",    // Purple
    };

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 220,
      layout: {
        background: { color: themeColors.bg },
        textColor: themeColors.text,
        fontSize: 11,
        fontFamily: "'Plus Jakarta Sans', sans-serif",
      },
      grid: {
        vertLines: { color: themeColors.grid },
        horzLines: { color: themeColors.grid },
      },
      rightPriceScale: {
        borderColor: themeColors.border,
        visible: true,
        minimumWidth: 80,
      },
      timeScale: {
        borderColor: themeColors.border,
        visible: true,
      },
      crosshair: {
        vertLine: {
          color: "#404048",
          width: 1,
          style: 3,
        },
        horzLine: {
          color: "#404048",
          width: 1,
          style: 3,
        },
      },
    });

    chartRef.current = chart;
    registerChart(chartId, chart);

    // Area series for stacked representation:
    // 1. Top Area (representing Bull) = p_sideways + p_bear + p_bull = 1.0
    const bullSeries = chart.addSeries(AreaSeries, {
      topColor: "rgba(16, 185, 129, 0.5)",
      bottomColor: "rgba(16, 185, 129, 0.05)",
      lineColor: "#10b981",
      lineWidth: 1,
      priceScaleId: "right",
    });

    // 2. Middle Area (representing Bear) = p_sideways + p_bear
    const bearSeries = chart.addSeries(AreaSeries, {
      topColor: "rgba(239, 68, 68, 0.5)",
      bottomColor: "rgba(239, 68, 68, 0.05)",
      lineColor: "#ef4444",
      lineWidth: 1,
      priceScaleId: "right",
    });

    // 3. Bottom Area (representing Sideways) = p_sideways
    const sidewaysSeries = chart.addSeries(AreaSeries, {
      topColor: "rgba(168, 85, 247, 0.5)",
      bottomColor: "rgba(168, 85, 247, 0.05)",
      lineColor: "#a855f7",
      lineWidth: 1,
      priceScaleId: "right",
    });

    // Sort unique timestamps
    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));
    const seenDates = new Set<string>();

    const bullData: any[] = [];
    const bearData: any[] = [];
    const sidewaysData: any[] = [];

    sortedData.forEach((r) => {
      if (seenDates.has(r.date)) return;
      seenDates.add(r.date);

      // Stack mathematically
      const vSideways = r.p_sideways;
      const vBear = vSideways + r.p_bear;
      const vBull = vBear + r.p_bull; // Sums to 1.0

      sidewaysData.push({ time: r.date, value: vSideways });
      bearData.push({ time: r.date, value: vBear });
      bullData.push({ time: r.date, value: vBull });
    });

    bullSeries.setData(bullData);
    bearSeries.setData(bearData);
    sidewaysSeries.setData(sidewaysData);

    // Register series for crosshair synchronization
    registerSeries(chartId, "bull", bullSeries, bullData);
    registerSeries(chartId, "bear", bearSeries, bearData);
    registerSeries(chartId, "sideways", sidewaysSeries, sidewaysData);

    // Coordinate scale zoom and pan
    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      syncTimeScale(chartId, range);
    });

    // Coordinate crosshair movements and local hover details
    const dataMap = new Map<string, RegimeRecord>(data.map((r) => [r.date, r]));
    chart.subscribeCrosshairMove((param) => {
      if (param.time) {
        syncCrosshair(chartId, param.time as string);
        const record = dataMap.get(param.time as string);
        if (record) setHoveredData(record);
      } else {
        syncCrosshair(chartId, null);
        setHoveredData(null);
      }
    });

    chart.timeScale().fitContent();

    return () => {
      unregisterChart(chartId);
      chart.remove();
      chartRef.current = null;
    };
  }, [data]);

  const pBull = activeState ? activeState.p_bull : 0;
  const pBear = activeState ? activeState.p_bear : 0;
  const pSideways = activeState ? activeState.p_sideways : 0;

  return (
    <div className="flex flex-col gap-2 bg-[#0a0a0f] p-6 rounded-3xl border border-[#202025]/50 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 px-2 py-1">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-purple-400">Layer 1 Regime Detection</span>
          <h3 className="text-sm font-semibold text-[#f3f4f6] mt-0.5">3-State HMM Probabilities</h3>
        </div>

        {activeState && (
          <div className="flex flex-wrap items-center gap-3 bg-white/5 border border-white/10 px-3.5 py-1.5 rounded-2xl text-[10px]">
            <span className="text-gray-500 font-mono">{activeState.date}</span>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
              <span className="text-gray-400">Bull: {(pBull * 100).toFixed(0)}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ef4444]"></span>
              <span className="text-gray-400">Bear: {(pBear * 100).toFixed(0)}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#a855f7]"></span>
              <span className="text-gray-400">Sideways: {(pSideways * 100).toFixed(0)}%</span>
            </div>

            {dominantRegime && (
              <span className={`ml-2 px-2 py-0.5 rounded-full font-bold border ${
                dominantRegime === "BULL"
                  ? "bg-[#10b981]/15 text-[#10b981] border-[#10b981]/25"
                  : dominantRegime === "BEAR"
                  ? "bg-[#ef4444]/15 text-[#ef4444] border-[#ef4444]/25"
                  : "bg-[#a855f7]/15 text-[#a855f7] border-[#a855f7]/25"
              }`}>
                {dominantRegime} DOMINANT
              </span>
            )}
          </div>
        )}
      </div>

      <div className="relative w-full h-[220px] rounded-2xl border border-[#202025]/30 bg-[#050505] overflow-hidden">
        <div ref={containerRef} className="w-full h-full" />
      </div>
    </div>
  );
};
