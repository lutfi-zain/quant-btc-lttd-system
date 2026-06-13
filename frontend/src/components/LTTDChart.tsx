/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/exhaustive-deps */
import React, { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries, AreaSeries, LineSeries, PriceScaleMode } from "lightweight-charts";
import type { IChartApi } from "lightweight-charts";
import { useSynchronizedCharts } from "./SynchronizedChartContext";
import type { ChartRecord } from "../api/client";

interface LTTDChartProps {
  data: ChartRecord[];
}

export const LTTDChart: React.FC<LTTDChartProps> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scoreContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const scoreChartRef = useRef<IChartApi | null>(null);
  const [scaleMode, setScaleMode] = useState<"linear" | "log">("linear");
  const { registerChart, unregisterChart, registerSeries, syncCrosshair, syncTimeScale } = useSynchronizedCharts();

  const chartId = "lttd-chart";
  const scoreChartId = "score-chart";

  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && containerRef.current) {
        chartRef.current.resize(containerRef.current.clientWidth, 400);
      }
      if (scoreChartRef.current && scoreContainerRef.current) {
        scoreChartRef.current.resize(scoreContainerRef.current.clientWidth, 200);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (!containerRef.current || !scoreContainerRef.current || data.length === 0) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
    if (scoreChartRef.current) {
      scoreChartRef.current.remove();
      scoreChartRef.current = null;
    }

    const themeColors = {
      bg: "#050505",
      grid: "#111115",
      text: "#8a8f98",
      border: "#202025",
      bull: "#10b981",
      bear: "#ef4444",
      score: "#8b5cf6",
      scoreFill: "rgba(139, 92, 246, 0.25)",
      hline: "rgba(255, 255, 255, 0.15)",
      hlineStrong: "rgba(16, 185, 129, 0.3)",
      hlineWeak: "rgba(255, 255, 255, 0.2)",
      hlineBear: "rgba(239, 68, 68, 0.3)",
    };

    // --- MAIN CHART (CANDLESTICK) ---
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 400,
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
        minimumWidth: 90,
        mode: scaleMode === "log" ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      },
      timeScale: {
        borderColor: themeColors.border,
        visible: false, // hide time scale on top chart since it's stacked
      },
      crosshair: {
        vertLine: { color: "#404048", width: 1, style: 3 },
        horzLine: { color: "#404048", width: 1, style: 3 },
      },
    });

    chartRef.current = chart;
    registerChart(chartId, chart);

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: themeColors.bull,
      downColor: themeColors.bear,
      borderUpColor: themeColors.bull,
      borderDownColor: themeColors.bear,
      wickUpColor: themeColors.bull,
      wickDownColor: themeColors.bear,
      priceScaleId: "right",
    });

    // --- SCORE CHART (SUUBPANEL) ---
    const scoreChart = createChart(scoreContainerRef.current, {
      width: scoreContainerRef.current.clientWidth,
      height: 200,
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
        minimumWidth: 90,
      },
      timeScale: {
        borderColor: themeColors.border,
        visible: true,
      },
      crosshair: {
        vertLine: { color: "#404048", width: 1, style: 3 },
        horzLine: { color: "#404048", width: 1, style: 3 },
      },
    });

    scoreChartRef.current = scoreChart;
    registerChart(scoreChartId, scoreChart);

    const scoreSeries = scoreChart.addSeries(AreaSeries, {
      topColor: themeColors.scoreFill,
      bottomColor: "rgba(139, 92, 246, 0.0)",
      lineColor: themeColors.score,
      lineWidth: 2,
      priceScaleId: "right",
    });

    // Add H-Lines
    const addHLine = (val: number, color: string, style: number) => {
      const line = scoreChart.addSeries(LineSeries, {
        color: color,
        lineWidth: 1,
        lineStyle: style,
        priceScaleId: "right",
      });
      return line;
    };

    const strongBullLine = addHLine(0.8, themeColors.hlineStrong, 2);
    const weakBullLine = addHLine(0.2, themeColors.hlineWeak, 2);
    const zeroLine = addHLine(0.0, themeColors.hline, 1);
    const weakBearLine = addHLine(-0.2, themeColors.hlineWeak, 2);
    const strongBearLine = addHLine(-0.8, themeColors.hlineBear, 2);

    // Format data
    const priceData: any[] = [];
    const scoreData: any[] = [];
    const lineDataSets = {
      sb: [] as any[],
      wb: [] as any[],
      z: [] as any[],
      wbe: [] as any[],
      sbe: [] as any[],
    };

    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));
    const seenDates = new Set<string>();

    sortedData.forEach((r) => {
      if (seenDates.has(r.date)) return;
      seenDates.add(r.date);

      if (r.open !== undefined && r.high !== undefined && r.low !== undefined && r.close !== undefined) {
        priceData.push({
          time: r.date,
          open: r.open,
          high: r.high,
          low: r.low,
          close: r.close,
        });
      }

      scoreData.push({
        time: r.date,
        value: r.final_score,
      });

      lineDataSets.sb.push({ time: r.date, value: 0.8 });
      lineDataSets.wb.push({ time: r.date, value: 0.2 });
      lineDataSets.z.push({ time: r.date, value: 0.0 });
      lineDataSets.wbe.push({ time: r.date, value: -0.2 });
      lineDataSets.sbe.push({ time: r.date, value: -0.8 });
    });

    candlestickSeries.setData(priceData);
    scoreSeries.setData(scoreData);
    strongBullLine.setData(lineDataSets.sb);
    weakBullLine.setData(lineDataSets.wb);
    zeroLine.setData(lineDataSets.z);
    weakBearLine.setData(lineDataSets.wbe);
    strongBearLine.setData(lineDataSets.sbe);

    // Lock price scales for the score chart to always show -1.0 to 1.0
    scoreSeries.applyOptions({
      autoscaleInfoProvider: () => ({
        priceRange: {
          minValue: -1.1,
          maxValue: 1.1,
        },
      }),
    });
    // Setting fixed range in Lightweight Charts v4 requires overriding minimum/maximum logic via autoScale=false, 
    // but the cleanest way is just to ensure the bounds are hit, which the hlines do.
    
    // Register series for sync
    registerSeries(chartId, "price", candlestickSeries, priceData.map((p) => ({ time: p.time, value: p.close })));
    registerSeries(scoreChartId, "score", scoreSeries, scoreData);

    // Main chart sync
    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      syncTimeScale(chartId, range);
    });
    chart.subscribeCrosshairMove((param) => {
      syncCrosshair(chartId, param.time as string | null);
    });

    // Score chart sync
    scoreChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      syncTimeScale(scoreChartId, range);
    });
    scoreChart.subscribeCrosshairMove((param) => {
      syncCrosshair(scoreChartId, param.time as string | null);
    });

    chart.timeScale().fitContent();
    scoreChart.timeScale().fitContent();

    return () => {
      unregisterChart(chartId);
      unregisterChart(scoreChartId);
      chart.remove();
      scoreChart.remove();
      chartRef.current = null;
      scoreChartRef.current = null;
    };
  }, [data, scaleMode]);

  return (
    <div className="flex flex-col gap-2 bg-[#0a0a0f] p-6 rounded-3xl border border-[#202025]/50 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl">
      <div className="flex justify-between items-center px-2 py-1">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-purple-400">Layer 4 Ensemble</span>
          <h3 className="text-sm font-semibold text-[#f3f4f6] mt-0.5">Bitcoin Candlestick & Final Score</h3>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setScaleMode(scaleMode === "log" ? "linear" : "log")}
            className={`px-3 py-1.5 rounded-full border text-[10px] font-semibold tracking-wider transition-all duration-300 shadow-md cursor-pointer ${
              scaleMode === "log"
                ? "bg-purple-500/20 text-purple-400 border-purple-500/40 hover:bg-purple-500/30"
                : "bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white"
            }`}
          >
            {scaleMode === "log" ? "LOG SCALE" : "LIN SCALE"}
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {/* Main Price Chart */}
        <div className="relative w-full h-[400px] rounded-t-2xl border border-[#202025]/30 bg-[#050505] overflow-hidden">
          <div ref={containerRef} className="w-full h-full" />
        </div>
        {/* Score Subpanel */}
        <div className="relative w-full h-[200px] rounded-b-2xl border border-[#202025]/30 bg-[#050505] overflow-hidden">
          <div ref={scoreContainerRef} className="w-full h-full" />
        </div>
      </div>
    </div>
  );
};

