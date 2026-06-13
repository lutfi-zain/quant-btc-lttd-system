/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/exhaustive-deps */
import React, { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries, AreaSeries, LineSeries, HistogramSeries, ColorType, PriceScaleMode } from "lightweight-charts";
import type { IChartApi } from "lightweight-charts";
import { useSynchronizedCharts } from "./SynchronizedChartContext";
import type { ChartRecord } from "../api/client";

interface LTTDChartProps {
  data: ChartRecord[];
}

export const LTTDChart: React.FC<LTTDChartProps> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scoreContainerRef = useRef<HTMLDivElement>(null);
  const exposureContainerRef = useRef<HTMLDivElement>(null);
  const equityContainerRef = useRef<HTMLDivElement>(null);
  
  const chartRef = useRef<IChartApi | null>(null);
  const scoreChartRef = useRef<IChartApi | null>(null);
  const exposureChartRef = useRef<IChartApi | null>(null);
  const equityChartRef = useRef<IChartApi | null>(null);
  
  const [scaleMode, setScaleMode] = useState<"linear" | "log">("log");
  const { registerChart, unregisterChart, registerSeries, syncCrosshair, syncTimeScale } = useSynchronizedCharts();

  const chartId = "lttd-chart";
  const scoreChartId = "score-chart";
  const exposureChartId = "exposure-chart";
  const equityChartId = "equity-chart";

  useEffect(() => {
    if (!containerRef.current || !scoreContainerRef.current || !exposureContainerRef.current || !equityContainerRef.current || data.length === 0) return;

    // Cleanup previous instances
    [chartRef, scoreChartRef, exposureChartRef, equityChartRef].forEach(ref => {
      if (ref.current) {
        ref.current.remove();
        ref.current = null;
      }
    });

    const getVar = (name: string, fallback: string) => {
      if (typeof window === 'undefined') return fallback;
      const val = getComputedStyle(document.documentElement).getPropertyValue(name);
      return val ? val.trim() : fallback;
    };

    const defaultBorder = getVar('--color-border', 'rgba(255,255,255,0.1)');

    const themeColors = {
      bg: 'transparent',
      grid: defaultBorder,
      text: getVar('--color-text-muted', '#a1a1aa'),
      border: defaultBorder,
      bull: getVar('--color-bull', '#10b981'),
      bear: getVar('--color-bear', '#ef4444'),
      score: getVar('--color-accent', '#0ea5e9'),
      equity: '#f59e0b',
      exposure: '#8b5cf6',
      crosshair: getVar('--color-text-primary', '#f4f4f5'),
      fontFamily: getVar('--font-mono', "'JetBrains Mono', monospace"),
    };

    const createCommonChart = (container: HTMLDivElement, showTimeScale: boolean, logScale: boolean = false) => {
      return createChart(container, {
        autoSize: true,
        layout: {
          background: { type: ColorType.Solid, color: themeColors.bg },
          textColor: themeColors.text,
          fontSize: 11,
          fontFamily: themeColors.fontFamily,
        },
        grid: {
          vertLines: { color: themeColors.grid, style: 1 },
          horzLines: { color: themeColors.grid, style: 1 },
        },
        rightPriceScale: {
          borderColor: themeColors.border,
          visible: true,
          minimumWidth: 90,
          mode: logScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
        },
        timeScale: {
          borderColor: themeColors.border,
          visible: showTimeScale,
        },
        crosshair: {
          vertLine: { color: themeColors.crosshair, width: 1, style: 3, labelBackgroundColor: themeColors.crosshair },
          horzLine: { color: themeColors.crosshair, width: 1, style: 3, labelBackgroundColor: themeColors.crosshair },
        },
      });
    };

    // 1. MAIN CHART
    const chart = createCommonChart(containerRef.current, false, scaleMode === "log");
    chartRef.current = chart;
    registerChart(chartId, chart);
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: themeColors.bull, downColor: themeColors.bear,
      borderUpColor: themeColors.bull, borderDownColor: themeColors.bear,
      wickUpColor: themeColors.bull, wickDownColor: themeColors.bear,
      priceScaleId: "right",
    });

    // 2. SCORE CHART
    const scoreChart = createCommonChart(scoreContainerRef.current, false);
    scoreChartRef.current = scoreChart;
    registerChart(scoreChartId, scoreChart);
    const scoreSeries = scoreChart.addSeries(AreaSeries, {
      topColor: themeColors.score,
      bottomColor: "rgba(14, 165, 233, 0.0)",
      lineColor: themeColors.score,
      lineWidth: 2,
      priceScaleId: "right",
    });

    // 3. EXPOSURE CHART
    const exposureChart = createCommonChart(exposureContainerRef.current, false);
    exposureChartRef.current = exposureChart;
    registerChart(exposureChartId, exposureChart);
    const exposureSeries = exposureChart.addSeries(HistogramSeries, {
      color: themeColors.exposure,
      priceScaleId: "right",
    });

    // 4. EQUITY CHART
    const equityChart = createCommonChart(equityContainerRef.current, true, scaleMode === "log");
    equityChartRef.current = equityChart;
    registerChart(equityChartId, equityChart);
    const equitySeries = equityChart.addSeries(LineSeries, {
      color: themeColors.equity,
      lineWidth: 2,
      priceScaleId: "right",
    });

    // Calculate simulated equity
    const priceData: any[] = [];
    const scoreData: any[] = [];
    const exposureData: any[] = [];
    const equityData: any[] = [];
    
    let equity = 1.0;
    let prevExposure = 0;
    
    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));
    sortedData.forEach((r, i) => {
      if (i > 0) {
        const prevR = sortedData[i - 1];
        if (prevR.close && r.close) {
          const dailyReturn = (r.close - prevR.close) / prevR.close;
          equity = equity * (1 + prevExposure * dailyReturn);
        }
      }
      
      priceData.push({ time: r.date, open: r.open, high: r.high, low: r.low, close: r.close });
      scoreData.push({ time: r.date, value: r.final_score });
      exposureData.push({ time: r.date, value: (r.target_exposure ?? 0) * 100 });
      equityData.push({ time: r.date, value: equity });
      
      prevExposure = r.target_exposure ?? 0;
    });

    candlestickSeries.setData(priceData);
    scoreSeries.setData(scoreData);
    exposureSeries.setData(exposureData);
    equitySeries.setData(equityData);

    registerSeries(chartId, "price", candlestickSeries, priceData.map((p) => ({ time: p.time, value: p.close })));
    registerSeries(scoreChartId, "score", scoreSeries, scoreData);
    registerSeries(exposureChartId, "exposure", exposureSeries, exposureData);
    registerSeries(equityChartId, "equity", equitySeries, equityData);

    const charts = [
      { id: chartId, chart },
      { id: scoreChartId, chart: scoreChart },
      { id: exposureChartId, chart: exposureChart },
      { id: equityChartId, chart: equityChart },
    ];

    charts.forEach(({ id, chart }) => {
      chart.timeScale().subscribeVisibleLogicalRangeChange((range) => syncTimeScale(id, range));
      chart.subscribeCrosshairMove((param) => syncCrosshair(id, param.time as string | null));
      chart.timeScale().fitContent();
    });

    return () => {
      charts.forEach(({ id, chart }) => {
        unregisterChart(id);
        chart.remove();
      });
    };
  }, [data, scaleMode]);

  return (
    <div className="flex flex-col gap-0 h-full relative">
      <div className="absolute -top-[4rem] right-0 z-20">
        <button
          onClick={() => setScaleMode(scaleMode === "log" ? "linear" : "log")}
          className="px-4 py-1.5 rounded-none border border-[var(--color-border)] text-[10px] font-bold tracking-[0.2em] bg-[var(--color-surface)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
        >
          {scaleMode === "log" ? "LOGARITHMIC" : "LINEAR"}
        </button>
      </div>

      <div className="w-full h-full flex flex-col group gap-0">
        <div className="relative w-full flex-[2] bg-transparent overflow-hidden min-h-[300px]">
          <div ref={containerRef} className="absolute inset-0" />
        </div>
        <div className="relative w-full flex-1 bg-transparent overflow-hidden min-h-[120px] mt-1">
          <div ref={scoreContainerRef} className="absolute inset-0" />
        </div>
        <div className="relative w-full flex-1 bg-transparent overflow-hidden min-h-[120px] mt-1">
          <div ref={exposureContainerRef} className="absolute inset-0" />
        </div>
        <div className="relative w-full flex-1 bg-transparent overflow-hidden min-h-[150px] mt-1">
          <div ref={equityContainerRef} className="absolute inset-0" />
        </div>
      </div>
    </div>
  );
};
