/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/exhaustive-deps */
import React, { useEffect, useRef, useState } from "react";
import { createChart, LineSeries } from "lightweight-charts";
import type { IChartApi } from "lightweight-charts";
import { useSynchronizedCharts } from "./SynchronizedChartContext";
import type { OnChainRecord } from "../api/client";

interface OnChainPanelProps {
  data: OnChainRecord[];
}

export const OnChainPanel: React.FC<OnChainPanelProps> = ({ data }) => {
  const mvrvContainerRef = useRef<HTMLDivElement>(null);
  const nuplContainerRef = useRef<HTMLDivElement>(null);
  
  const mvrvChartRef = useRef<IChartApi | null>(null);
  const nuplChartRef = useRef<IChartApi | null>(null);
  
  const [hoveredData, setHoveredData] = useState<OnChainRecord | null>(null);

  const { registerChart, unregisterChart, registerSeries, syncCrosshair, syncTimeScale } = useSynchronizedCharts();

  const mvrvChartId = "onchain-mvrv-chart";
  const nuplChartId = "onchain-nupl-chart";

  useEffect(() => {
    const handleResize = () => {
      if (mvrvChartRef.current && mvrvContainerRef.current) {
        mvrvChartRef.current.resize(mvrvContainerRef.current.clientWidth, 160);
      }
      if (nuplChartRef.current && nuplContainerRef.current) {
        nuplChartRef.current.resize(nuplContainerRef.current.clientWidth, 160);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (!mvrvContainerRef.current || !nuplContainerRef.current || data.length === 0) return;

    // Clean up
    if (mvrvChartRef.current) {
      mvrvChartRef.current.remove();
      mvrvChartRef.current = null;
    }
    if (nuplChartRef.current) {
      nuplChartRef.current.remove();
      nuplChartRef.current = null;
    }

    const themeColors = {
      bg: "#FFFFFF",
      grid: "#EAEAEA",
      text: "#787774",
      border: "#EAEAEA",
      mvrv: "#1F6C9F", // Muted blue
      nupl: "#9F2F2D", // Muted red
      alert: "#9F2F2D",
    };

    const commonOptions = {
      layout: {
        background: { color: themeColors.bg },
        textColor: themeColors.text,
        fontSize: 10,
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
        vertLine: { color: "#D1D1D1", width: 1 as any, style: 3 as any },
        horzLine: { color: "#D1D1D1", width: 1 as any, style: 3 as any },
      },
    };

    // 1. STH-MVRV Chart
    const mvrvChart = createChart(mvrvContainerRef.current, {
      ...commonOptions,
      height: 160,
      timeScale: { ...commonOptions.timeScale, visible: false }, // Hide bottom scale to stack neatly
    });
    mvrvChartRef.current = mvrvChart;
    registerChart(mvrvChartId, mvrvChart);

    const mvrvSeries = mvrvChart.addSeries(LineSeries, {
      color: themeColors.mvrv,
      lineWidth: 2,
      priceScaleId: "right",
    });

    // Demarcate override threshold line (2.0)
    mvrvSeries.createPriceLine({
      price: 2.0,
      color: themeColors.alert,
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "OVERRIDE (>2.0)",
    });

    // 2. STH-NUPL Chart
    const nuplChart = createChart(nuplContainerRef.current, {
      ...commonOptions,
      height: 160,
    });
    nuplChartRef.current = nuplChart;
    registerChart(nuplChartId, nuplChart);

    const nuplSeries = nuplChart.addSeries(LineSeries, {
      color: themeColors.nupl,
      lineWidth: 2,
      priceScaleId: "right",
    });

    // Demarcate override threshold line (0.75)
    nuplSeries.createPriceLine({
      price: 0.75,
      color: themeColors.alert,
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "OVERRIDE (>0.75)",
    });

    // Format and Sort Data
    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));
    const seenDates = new Set<string>();

    const mvrvData: any[] = [];
    const nuplData: any[] = [];

    sortedData.forEach((r) => {
      if (seenDates.has(r.date)) return;
      seenDates.add(r.date);

      if (r.sth_mvrv !== undefined) {
        mvrvData.push({ time: r.date, value: r.sth_mvrv });
      }
      if (r.sth_nupl !== undefined) {
        nuplData.push({ time: r.date, value: r.sth_nupl });
      }
    });

    mvrvSeries.setData(mvrvData);
    nuplSeries.setData(nuplData);

    // Register series for crosshair sync
    registerSeries(mvrvChartId, "mvrv", mvrvSeries, mvrvData);
    registerSeries(nuplChartId, "nupl", nuplSeries, nuplData);

    // Zoom sync between the two charts
    mvrvChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      syncTimeScale(mvrvChartId, range);
    });
    nuplChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      syncTimeScale(nuplChartId, range);
    });

    // Hover/crosshair sync
    const dataMap = new Map<string, OnChainRecord>(data.map((r) => [r.date, r]));

    const handleMvrvMove = (param: any) => {
      if (param.time) {
        syncCrosshair(mvrvChartId, param.time as string);
        const record = dataMap.get(param.time as string);
        if (record) setHoveredData(record);
      } else {
        syncCrosshair(mvrvChartId, null);
        setHoveredData(null);
      }
    };

    const handleNuplMove = (param: any) => {
      if (param.time) {
        syncCrosshair(nuplChartId, param.time as string);
        const record = dataMap.get(param.time as string);
        if (record) setHoveredData(record);
      } else {
        syncCrosshair(nuplChartId, null);
        setHoveredData(null);
      }
    };

    mvrvChart.subscribeCrosshairMove(handleMvrvMove);
    nuplChart.subscribeCrosshairMove(handleNuplMove);

    mvrvChart.timeScale().fitContent();
    nuplChart.timeScale().fitContent();

    return () => {
      unregisterChart(mvrvChartId);
      unregisterChart(nuplChartId);
      if (mvrvChartRef.current) mvrvChartRef.current.remove();
      if (nuplChartRef.current) nuplChartRef.current.remove();
      mvrvChartRef.current = null;
      nuplChartRef.current = null;
    };
  }, [data]);

  const latestVal = data.length > 0 ? data[data.length - 1] : null;
  const activeVal = hoveredData || latestVal;

  const isMvrvAlert = activeVal && activeVal.sth_mvrv !== undefined && activeVal.sth_mvrv > 2.0;
  const isNuplAlert = activeVal && activeVal.sth_nupl !== undefined && activeVal.sth_nupl > 0.75;

  return (
    <div className="flex flex-col gap-6 h-full">
      {activeVal && (
        <div className="flex flex-wrap items-center gap-3 bg-[var(--color-surface)] border border-[var(--color-border)] px-4 py-2 rounded text-[10px]">
          <span className="text-[var(--color-text-muted)] font-mono uppercase tracking-wider">{activeVal.date}</span>
          <div className="w-[1px] h-3 bg-[#EAEAEA]"></div>
          <div className="flex items-center gap-2">
            <span className="text-[var(--color-text-muted)] font-medium tracking-wider">STH-MVRV</span>
            <span className={`font-mono ${isMvrvAlert ? "text-[var(--color-bear)]" : "text-[var(--color-text-primary)]"}`}>
              {activeVal.sth_mvrv?.toFixed(2) ?? "N/A"}
            </span>
            {isMvrvAlert && (
              <span className="px-1.5 py-0.5 bg-[var(--color-surface)] text-[var(--color-bear)] border border-[var(--color-bear)] rounded font-medium text-[8px] tracking-widest uppercase">
                Euphoria
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[var(--color-text-muted)] font-medium tracking-wider">STH-NUPL</span>
            <span className={`font-mono ${isNuplAlert ? "text-[var(--color-bear)]" : "text-[var(--color-text-primary)]"}`}>
              {activeVal.sth_nupl?.toFixed(2) ?? "N/A"}
            </span>
            {isNuplAlert && (
              <span className="px-1.5 py-0.5 bg-[var(--color-surface)] text-[var(--color-bear)] border border-[var(--color-bear)] rounded font-medium text-[8px] tracking-widest uppercase">
                Alert
              </span>
            )}
          </div>
        </div>
      )}

      {/* STH-MVRV Chart Container */}
      <div className="flex flex-col gap-2">
        <span className="text-[9px] uppercase tracking-[0.1em] font-medium text-[var(--color-text-muted)] px-1 font-mono">Short-Term Holder MVRV</span>
        <div className="relative w-full h-[160px] rounded border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
          <div ref={mvrvContainerRef} className="absolute inset-0" />
        </div>
      </div>

      {/* STH-NUPL Chart Container */}
      <div className="flex flex-col gap-2">
        <span className="text-[9px] uppercase tracking-[0.1em] font-medium text-[var(--color-text-muted)] px-1 font-mono">Short-Term Holder NUPL</span>
        <div className="relative w-full h-[160px] rounded border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
          <div ref={nuplContainerRef} className="absolute inset-0" />
        </div>
      </div>
    </div>
  );
};
