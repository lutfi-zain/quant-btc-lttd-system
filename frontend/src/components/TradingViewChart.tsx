/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/exhaustive-deps, prefer-const, no-useless-assignment */
import React, { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries, AreaSeries, LineSeries, PriceScaleMode, createSeriesMarkers } from "lightweight-charts";
import type { IChartApi, ISeriesApi, CandlestickData, LineData } from "lightweight-charts";
import type { LTTDRecord } from "../api/client";

interface TradingViewChartProps {
  data: LTTDRecord[];
}

export const TradingViewChart: React.FC<TradingViewChartProps> = ({ data }) => {
  const priceChartContainerRef = useRef<HTMLDivElement>(null);
  const scoreChartContainerRef = useRef<HTMLDivElement>(null);
  
  const priceChartRef = useRef<IChartApi | null>(null);
  const scoreChartRef = useRef<IChartApi | null>(null);

  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const scoreSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  const pc1SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const pc2SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const pc3SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const [showPCA, setShowPCA] = useState<boolean>(false);
  const [priceScaleMode, setPriceScaleMode] = useState<"linear" | "log">("linear");
  const [scoreScaleMode, setScoreScaleMode] = useState<"linear" | "log">("linear");

  // Resize charts on container resize
  useEffect(() => {
    const handleResize = () => {
      if (priceChartRef.current && priceChartContainerRef.current) {
        priceChartRef.current.resize(
          priceChartContainerRef.current.clientWidth,
          350
        );
      }
      if (scoreChartRef.current && scoreChartContainerRef.current) {
        scoreChartRef.current.resize(
          scoreChartContainerRef.current.clientWidth,
          150
        );
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Initialize and update charts
  useEffect(() => {
    if (!priceChartContainerRef.current || !scoreChartContainerRef.current || data.length === 0) {
      return;
    }

    // --- 1. Clean up existing charts ---
    if (priceChartRef.current) {
      priceChartRef.current.remove();
      priceChartRef.current = null;
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
      pca1: "#22d3ee", // Cyan
      pca2: "#ec4899", // Pink
      pca3: "#f59e0b", // Amber
    };

    // --- 2. Create Price Chart (Top Pane) ---
    const priceChart = createChart(priceChartContainerRef.current, {
      width: priceChartContainerRef.current.clientWidth,
      height: 350,
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
        mode: priceScaleMode === "log" ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      },
      leftPriceScale: {
        borderColor: themeColors.border,
        visible: showPCA, // Only show PCA axis if toggled
        minimumWidth: 80,
      },
      timeScale: {
        borderColor: themeColors.border,
        visible: false, // Hide time scale on top chart, synchronized with bottom
      },
      crosshair: {
        vertLine: {
          color: "#404048",
          width: 1,
          style: 3, // dashed
        },
        horzLine: {
          color: "#404048",
          width: 1,
          style: 3,
        },
      },
    });

    const candlestickSeries = priceChart.addSeries(CandlestickSeries, {
      upColor: themeColors.bull,
      downColor: themeColors.bear,
      borderUpColor: themeColors.bull,
      borderDownColor: themeColors.bear,
      wickUpColor: themeColors.bull,
      wickDownColor: themeColors.bear,
    });

    priceChartRef.current = priceChart;
    candlestickSeriesRef.current = candlestickSeries;

    // --- 3. Create Score Chart (Bottom Pane) ---
    const scoreChart = createChart(scoreChartContainerRef.current, {
      width: scoreChartContainerRef.current.clientWidth,
      height: 150,
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
        mode: scoreScaleMode === "log" ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      },
      leftPriceScale: {
        borderColor: themeColors.border,
        visible: showPCA, // keep in sync with top chart left scale
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

    const scoreSeries = scoreChart.addSeries(AreaSeries, {
      topColor: "rgba(168, 85, 247, 0.4)", // Purple
      bottomColor: "rgba(168, 85, 247, 0.0)",
      lineColor: "#a855f7",
      lineWidth: 2,
      priceScaleId: "right",
    });

    scoreChartRef.current = scoreChart;
    scoreSeriesRef.current = scoreSeries;

    // --- 4. Populate Data ---
    const chartCandles: CandlestickData[] = [];
    const chartScores: AreaData[] = [];
    const pc1Data: LineData[] = [];
    const pc2Data: LineData[] = [];
    const pc3Data: LineData[] = [];

    // Lightweight charts requires sorted unique times
    const seenTimes = new Set<string>();

    data.forEach((r) => {
      const time = r.date;
      if (seenTimes.has(time)) return;
      seenTimes.add(time);

      if (r.open !== undefined && r.high !== undefined && r.low !== undefined && r.close !== undefined) {
        chartCandles.push({
          time,
          open: r.open,
          high: r.high,
          low: r.low,
          close: r.close,
        });
      }

      chartScores.push({
        time,
        value: r.final_score,
      });

      if (r.pca_components) {
        if (r.pca_components["PC1"] !== undefined) pc1Data.push({ time, value: r.pca_components["PC1"] });
        if (r.pca_components["PC2"] !== undefined) pc2Data.push({ time, value: r.pca_components["PC2"] });
        if (r.pca_components["PC3"] !== undefined) pc3Data.push({ time, value: r.pca_components["PC3"] });
      }
    });

    candlestickSeries.setData(chartCandles);
    scoreSeries.setData(chartScores);

    // --- Transition Markers (Regime Shift Visualization) ---
    const markers: any[] = [];
    for (let i = 1; i < data.length; i++) {
      if (data[i].regime !== data[i - 1].regime) {
        const time = data[i].date;
        const prevRegime = data[i - 1].regime;
        const nextRegime = data[i].regime;
        
        let color = "#a855f7"; // purple for sideways
        let shape: "arrowUp" | "arrowDown" | "circle" = "circle";
        let position: "aboveBar" | "belowBar" | "inBar" = "belowBar";
        let text = `${prevRegime} → ${nextRegime}`;

        if (nextRegime === "BULL") {
          color = themeColors.bull;
          shape = "arrowUp";
          position = "belowBar";
        } else if (nextRegime === "BEAR") {
          color = themeColors.bear;
          shape = "arrowDown";
          position = "aboveBar";
        } else {
          // SIDEWAYS
          color = "#a855f7";
          shape = "circle";
          position = "belowBar";
        }

        markers.push({
          time,
          position,
          shape,
          color,
          text,
          size: 1,
        });
      }
    }
    createSeriesMarkers(candlestickSeries, markers);

    // --- 5. Add PCA series if toggled ---
    if (showPCA) {
      const pc1Series = priceChart.addSeries(LineSeries, {
        color: themeColors.pca1,
        lineWidth: 2,
        priceScaleId: "left",
      });
      const pc2Series = priceChart.addSeries(LineSeries, {
        color: themeColors.pca2,
        lineWidth: 2,
        priceScaleId: "left",
      });
      const pc3Series = priceChart.addSeries(LineSeries, {
        color: themeColors.pca3,
        lineWidth: 2,
        priceScaleId: "left",
      });

      pc1Series.setData(pc1Data);
      pc2Series.setData(pc2Data);
      pc3Series.setData(pc3Data);

      pc1SeriesRef.current = pc1Series;
      pc2SeriesRef.current = pc2Series;
      pc3SeriesRef.current = pc3Series;

      priceChart.priceScale("left").applyOptions({
        borderColor: themeColors.border,
        visible: true,
      });
    }

    // --- 6. Synchronize Zoom and Time Scale ---
    let isSyncing = false;

    const priceTimeScale = priceChart.timeScale();
    const scoreTimeScale = scoreChart.timeScale();

    priceTimeScale.subscribeVisibleLogicalRangeChange((range) => {
      if (isSyncing) return;
      isSyncing = true;
      if (range) scoreTimeScale.setVisibleLogicalRange(range);
      isSyncing = false;
    });

    scoreTimeScale.subscribeVisibleLogicalRangeChange((range) => {
      if (isSyncing) return;
      isSyncing = true;
      if (range) priceTimeScale.setVisibleLogicalRange(range);
      isSyncing = false;
    });

    // --- 7. Synchronize Crosshair Cursor Movement ---
    const dataMap = new Map<string, LTTDRecord>(data.map((r) => [r.date, r]));

    const handlePriceCrosshairMove = (param: any) => {
      if (!param.sourceEvent) return; // ignore programmatic updates
      
      if (param.time && param.point) {
        const record = dataMap.get(param.time as string);
        if (record && record.final_score !== undefined) {
          scoreChart.setCrosshairPosition(record.final_score, param.time, scoreSeries);
        } else {
          scoreChart.clearCrosshairPosition();
        }
      } else {
        scoreChart.clearCrosshairPosition();
      }
    };

    const handleScoreCrosshairMove = (param: any) => {
      if (!param.sourceEvent) return; // ignore programmatic updates

      if (param.time && param.point) {
        const record = dataMap.get(param.time as string);
        if (record && record.close !== undefined) {
          priceChart.setCrosshairPosition(record.close, param.time, candlestickSeries);
        } else {
          priceChart.clearCrosshairPosition();
        }
      } else {
        priceChart.clearCrosshairPosition();
      }
    };

    priceChart.subscribeCrosshairMove(handlePriceCrosshairMove);
    scoreChart.subscribeCrosshairMove(handleScoreCrosshairMove);

    // Fit content initially
    priceTimeScale.fitContent();
    scoreTimeScale.fitContent();

    return () => {
      if (priceChartRef.current) {
        priceChartRef.current.unsubscribeCrosshairMove(handlePriceCrosshairMove);
        priceChartRef.current.remove();
        priceChartRef.current = null;
      }
      if (scoreChartRef.current) {
        scoreChartRef.current.unsubscribeCrosshairMove(handleScoreCrosshairMove);
        scoreChartRef.current.remove();
        scoreChartRef.current = null;
      }
    };

  }, [data, showPCA, priceScaleMode, scoreScaleMode]);

  return (
    <div className="flex flex-col gap-2 bg-[#0a0a0f] p-4 rounded-none border border-[#202025]/50 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl">
      <div className="flex justify-between items-center px-2 py-1">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-purple-400">Layer 6 telemetry</span>
          <h3 className="text-sm font-semibold text-[#f3f4f6] mt-0.5">Bitcoin Trend Candlestick & Signal Coherence</h3>
        </div>
        <button
          onClick={() => setShowPCA(!showPCA)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-none text-xs font-medium border transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] ${
            showPCA
              ? "bg-[#22d3ee]/10 text-[#22d3ee] border-[#22d3ee]/30"
              : "bg-white/5 text-gray-400 border-white/10 hover:bg-white/10"
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-none ${showPCA ? "bg-[#22d3ee] animate-pulse" : "bg-gray-500"}`}></span>
          PCA Overlay
        </button>
      </div>

      {/* Primary Pane (Price Candlestick) */}
      <div className="relative w-full h-[350px] rounded-none border border-[#202025]/30 bg-[#050505] overflow-hidden">
        <div ref={priceChartContainerRef} className="w-full h-full" />
        <div className="absolute top-3 right-3 z-10 flex gap-2">
          <button
            onClick={() => setPriceScaleMode(priceScaleMode === "log" ? "linear" : "log")}
            className={`px-2.5 py-1 rounded-none border text-[10px] font-semibold tracking-wider transition-all duration-300 shadow-md cursor-pointer ${
              priceScaleMode === "log"
                ? "bg-purple-500/20 text-purple-400 border-purple-500/40 hover:bg-purple-500/30"
                : "bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white"
            }`}
          >
            {priceScaleMode === "log" ? "LOG" : "LIN"}
          </button>
        </div>
      </div>

      {/* Secondary Pane (LTTD Score) */}
      <div className="relative w-full h-[150px] rounded-none border border-[#202025]/30 bg-[#050505] overflow-hidden">
        <div ref={scoreChartContainerRef} className="w-full h-full" />
        <div className="absolute top-3 right-3 z-10 flex gap-2">
          <button
            onClick={() => setScoreScaleMode(scoreScaleMode === "log" ? "linear" : "log")}
            className={`px-2.5 py-1 rounded-none border text-[10px] font-semibold tracking-wider transition-all duration-300 shadow-md cursor-pointer ${
              scoreScaleMode === "log"
                ? "bg-purple-500/20 text-purple-400 border-purple-500/40 hover:bg-purple-500/30"
                : "bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white"
            }`}
          >
            {scoreScaleMode === "log" ? "LOG" : "LIN"}
          </button>
        </div>
      </div>
      
      {showPCA && (
        <div className="flex flex-wrap gap-4 px-2 py-1.5 border-t border-[#202025]/30 mt-1">
          <div className="flex items-center gap-2 text-[10px] font-medium text-gray-400">
            <span className="w-2.5 h-0.5 bg-[#22d3ee]"></span>
            <span>PC1 (Trend Direction)</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] font-medium text-gray-400">
            <span className="w-2.5 h-0.5 bg-[#ec4899]"></span>
            <span>PC2 (Regime Volatility)</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] font-medium text-gray-400">
            <span className="w-2.5 h-0.5 bg-[#f59e0b]"></span>
            <span>PC3 (On-chain Momentum)</span>
          </div>
        </div>
      )}
    </div>
  );
};

// Supporting type definitions for Area Data compatibility
type AreaData = {
  time: string;
  value: number;
};
