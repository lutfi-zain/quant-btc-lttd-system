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
  const chartRef = useRef<IChartApi | null>(null);
  const [scaleMode, setScaleMode] = useState<"linear" | "log">("linear");
  const { registerChart, unregisterChart, registerSeries, syncCrosshair, syncTimeScale } = useSynchronizedCharts();

  const chartId = "lttd-chart";

  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && containerRef.current) {
        chartRef.current.resize(containerRef.current.clientWidth, 400);
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
      bull: "#10b981",
      bear: "#ef4444",
      score: "#8b5cf6",
    };

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
        minimumWidth: 80,
        mode: scaleMode === "log" ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      },
      leftPriceScale: {
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

    // Price series on the right y-axis
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: themeColors.bull,
      downColor: themeColors.bear,
      borderUpColor: themeColors.bull,
      borderDownColor: themeColors.bear,
      wickUpColor: themeColors.bull,
      wickDownColor: themeColors.bear,
      priceScaleId: "right",
    });

    // Score series on the left y-axis
    const scoreSeries = chart.addSeries(AreaSeries, {
      topColor: "rgba(139, 92, 246, 0.35)",
      bottomColor: "rgba(139, 92, 246, 0.0)",
      lineColor: themeColors.score,
      lineWidth: 2,
      priceScaleId: "left",
    });

    // Bounded reference lines for score (-1.0, 0, 1.0)
    const upperLimitSeries = chart.addSeries(LineSeries, {
      color: "rgba(239, 68, 68, 0.2)",
      lineWidth: 1,
      lineStyle: 2, // Dashed
      priceScaleId: "left",
    });

    const lowerLimitSeries = chart.addSeries(LineSeries, {
      color: "rgba(239, 68, 68, 0.2)",
      lineWidth: 1,
      lineStyle: 2,
      priceScaleId: "left",
    });

    const zeroLineSeries = chart.addSeries(LineSeries, {
      color: "rgba(255, 255, 255, 0.15)",
      lineWidth: 1,
      lineStyle: 1, // Solid
      priceScaleId: "left",
    });

    // Format data
    const priceData: any[] = [];
    const scoreData: any[] = [];
    const upperLimitData: any[] = [];
    const lowerLimitData: any[] = [];
    const zeroLineData: any[] = [];

    // Sort unique timestamps
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

      upperLimitData.push({ time: r.date, value: 1.0 });
      lowerLimitData.push({ time: r.date, value: -1.0 });
      zeroLineData.push({ time: r.date, value: 0.0 });
    });

    candlestickSeries.setData(priceData);
    scoreSeries.setData(scoreData);
    upperLimitSeries.setData(upperLimitData);
    lowerLimitSeries.setData(lowerLimitData);
    zeroLineSeries.setData(zeroLineData);

    // Register series for sync (use close price as coordinate value)
    registerSeries(
      chartId,
      "price",
      candlestickSeries,
      priceData.map((p) => ({ time: p.time, value: p.close }))
    );

    // Coordinate scale zoom and pan
    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      syncTimeScale(chartId, range);
    });

    // Coordinate crosshair movements
    chart.subscribeCrosshairMove((param) => {
      if (param.time) {
        syncCrosshair(chartId, param.time as string);
      } else {
        syncCrosshair(chartId, null);
      }
    });

    chart.timeScale().fitContent();

    return () => {
      unregisterChart(chartId);
      chart.remove();
      chartRef.current = null;
    };
  }, [data, scaleMode]);

  return (
    <div className="flex flex-col gap-2 bg-[#0a0a0f] p-6 rounded-3xl border border-[#202025]/50 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl">
      <div className="flex justify-between items-center px-2 py-1">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-purple-400">Layer 4 Ensemble</span>
          <h3 className="text-sm font-semibold text-[#f3f4f6] mt-0.5">Bitcoin Candlestick & Final Score overlay</h3>
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

      <div className="relative w-full h-[400px] rounded-2xl border border-[#202025]/30 bg-[#050505] overflow-hidden">
        <div ref={containerRef} className="w-full h-full" />
      </div>
    </div>
  );
};
