/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/exhaustive-deps */
import React, { useEffect, useRef, useState } from "react";
import { createChart, AreaSeries, ColorType } from "lightweight-charts";
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

    const getVar = (name: string, fallback: string) => {
      if (typeof window === 'undefined') return fallback;
      const val = getComputedStyle(document.documentElement).getPropertyValue(name);
      return val ? val.trim() : fallback;
    };

    const defaultBorder = getVar('--color-border', 'rgba(255,255,255,0.1)');
    const themeColors = {
      bg: "transparent",
      grid: defaultBorder,
      text: getVar('--color-text-muted', '#a1a1aa'),
      border: defaultBorder,
      fontFamily: getVar('--font-mono', "'JetBrains Mono', monospace"),
      crosshair: getVar('--color-text-primary', '#f4f4f5'),
      bull: getVar('--color-bull', '#10b981'),
      bear: getVar('--color-bear', '#ef4444'),
      sideways: getVar('--color-sideways', '#f59e0b'),
    };

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 220,
      layout: {
        background: { type: ColorType.Solid, color: themeColors.bg },
        textColor: themeColors.text,
        fontSize: 11,
        fontFamily: themeColors.fontFamily,
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
          color: themeColors.crosshair,
          width: 1,
          style: 3,
        },
        horzLine: {
          color: themeColors.crosshair,
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
      topColor: "rgba(16, 185, 129, 0.3)",
      bottomColor: "rgba(16, 185, 129, 0.05)",
      lineColor: themeColors.bull,
      lineWidth: 1,
      priceScaleId: "right",
    });

    // 2. Middle Area (representing Bear) = p_sideways + p_bear
    const bearSeries = chart.addSeries(AreaSeries, {
      topColor: "rgba(239, 68, 68, 0.3)",
      bottomColor: "rgba(239, 68, 68, 0.05)",
      lineColor: themeColors.bear,
      lineWidth: 1,
      priceScaleId: "right",
    });

    // 3. Bottom Area (representing Sideways) = p_sideways
    const sidewaysSeries = chart.addSeries(AreaSeries, {
      topColor: "rgba(245, 158, 11, 0.3)",
      bottomColor: "rgba(245, 158, 11, 0.05)",
      lineColor: themeColors.sideways,
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

  const getRegimeColor = (regime: string) => {
    switch (regime) {
      case "BULL": return { bg: "bg-[var(--color-surface)]", border: "border-[var(--color-border)]", text: "text-[var(--color-bull)]" };
      case "BEAR": return { bg: "bg-[var(--color-surface)]", border: "border-[var(--color-border)]", text: "text-[var(--color-bear)]" };
      default: return { bg: "bg-[var(--color-surface)]", border: "border-[var(--color-border)]", text: "text-[var(--color-sideways)]" };
    }
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      {activeState && (
        <div className="flex flex-wrap items-center gap-3 bg-[var(--color-surface)] border border-[var(--color-border)] px-4 py-2 rounded text-[10px]">
          <span className="text-[var(--color-text-muted)] font-[var(--font-mono)] tracking-wider">{activeState.date}</span>
          <div className="w-[1px] h-3 bg-[var(--color-border)]"></div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-none bg-[var(--color-bull)]"></span>
            <span className="text-[var(--color-text-primary)] font-[var(--font-mono)]">Bull: {(pBull * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-none bg-[var(--color-bear)]"></span>
            <span className="text-[var(--color-text-primary)] font-[var(--font-mono)]">Bear: {(pBear * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-none bg-[var(--color-sideways)]"></span>
            <span className="text-[var(--color-text-primary)] font-[var(--font-mono)]">Side: {(pSideways * 100).toFixed(0)}%</span>
          </div>

          {dominantRegime && (
            <span className={`ml-auto px-2 py-0.5 rounded font-medium tracking-widest uppercase border text-[9px] ${
              (() => {
                const colors = getRegimeColor(dominantRegime);
                return `${colors.bg} ${colors.border} ${colors.text}`;
              })()
            }`}>
              {dominantRegime} DOMINANT
            </span>
          )}
        </div>
      )}

      <div className="relative flex-1 w-full rounded border border-[var(--color-border)] bg-transparent overflow-hidden min-h-[220px]">
        <div ref={containerRef} className="absolute inset-0" />
      </div>
    </div>
  );
};

