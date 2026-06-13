/* eslint-disable react-refresh/only-export-components, @typescript-eslint/no-explicit-any */
import React, { createContext, useContext, useRef, useCallback } from "react";
import type { IChartApi, ISeriesApi } from "lightweight-charts";

type AllowedSeries = ISeriesApi<any>;

interface ChartRegistry {
  chart: IChartApi;
  seriesMap: Map<string, { series: AllowedSeries; dataMap: Map<string, number> }>;
}

interface SynchronizedChartContextType {
  registerChart: (id: string, chart: IChartApi) => void;
  unregisterChart: (id: string) => void;
  registerSeries: (chartId: string, seriesId: string, series: AllowedSeries, data: { time: string; value: number }[]) => void;
  syncCrosshair: (sourceChartId: string, time: string | null) => void;
  syncTimeScale: (sourceChartId: string, range: unknown) => void;
}

const SynchronizedChartContext = createContext<SynchronizedChartContextType | null>(null);

export const useSynchronizedCharts = () => {
  const context = useContext(SynchronizedChartContext);
  if (!context) {
    throw new Error("useSynchronizedCharts must be used within a SynchronizedChartProvider");
  }
  return context;
};

export const SynchronizedChartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const registry = useRef<Map<string, ChartRegistry>>(new Map());
  const isSyncingCrosshair = useRef<boolean>(false);
  const isSyncingTimeScale = useRef<boolean>(false);

  const registerChart = useCallback((id: string, chart: IChartApi) => {
    registry.current.set(id, {
      chart,
      seriesMap: new Map(),
    });
  }, []);

  const unregisterChart = useCallback((id: string) => {
    registry.current.delete(id);
  }, []);

  const registerSeries = useCallback((
    chartId: string,
    seriesId: string,
    series: AllowedSeries,
    data: { time: string; value: number }[]
  ) => {
    const chartInfo = registry.current.get(chartId);
    if (!chartInfo) return;

    const dataMap = new Map<string, number>();
    data.forEach((d) => {
      dataMap.set(d.time, d.value);
    });

    chartInfo.seriesMap.set(seriesId, { series, dataMap });
  }, []);

  const syncCrosshair = useCallback((sourceChartId: string, time: string | null) => {
    if (isSyncingCrosshair.current) return;
    isSyncingCrosshair.current = true;

    registry.current.forEach((info, chartId) => {
      if (chartId === sourceChartId) return;

      if (!time) {
        info.chart.clearCrosshairPosition();
        return;
      }

      // Find first registered series to position the crosshair
      const firstSeriesEntry = Array.from(info.seriesMap.values())[0];
      if (firstSeriesEntry) {
        const val = firstSeriesEntry.dataMap.get(time);
        if (val !== undefined) {
          info.chart.setCrosshairPosition(val, time, firstSeriesEntry.series);
        } else {
          info.chart.clearCrosshairPosition();
        }
      }
    });

    isSyncingCrosshair.current = false;
  }, []);

  const syncTimeScale = useCallback((sourceChartId: string, range: unknown) => {
    if (isSyncingTimeScale.current || !range) return;
    isSyncingTimeScale.current = true;

    registry.current.forEach((info, chartId) => {
      if (chartId === sourceChartId) return;
      info.chart.timeScale().setVisibleLogicalRange(range as any);
    });

    isSyncingTimeScale.current = false;
  }, []);

  return (
    <SynchronizedChartContext.Provider
      value={{
        registerChart,
        unregisterChart,
        registerSeries,
        syncCrosshair,
        syncTimeScale,
      }}
    >
      {children}
    </SynchronizedChartContext.Provider>
  );
};

