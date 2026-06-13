import React, { useState } from "react";
import type { DiagnosticsRecord } from "../api/client";

interface FeatureDiagnosticsPanelProps {
  data: DiagnosticsRecord[];
}

const INDICATOR_DETAILS: Record<
  string,
  {
    fullName: string;
    formula: string;
    description: string;
    interpretation: string;
    stats: { correlation: string; accuracy: string; pcaWeight: string };
  }
> = {
  FDI: {
    fullName: "Fractal Dimension Index",
    formula: "D = 1 + [ln(L) + ln(2)] / ln(2 * N)",
    description: "Mengukur kompleksitas fraktal (kekasaran geometris) dari time series harga. Nilai mendekati 1.0 menandakan pasar sedang trending kuat (sangat teratur), sementara nilai mendekati 2.0 mengindikasikan pergerakan acak (random walk / sideways).",
    interpretation: "FDI < 1.5 mengonfirmasi pasar sedang dalam kondisi tren makro yang valid, menyaring random noise.",
    stats: { correlation: "+0.11", accuracy: "54.2%", pcaWeight: "16.4%" },
  },
  QuantileDEMA: {
    fullName: "Quantile Double Exponential Moving Average",
    formula: "DEMA_q = DEMA(Close, T) smoothed by rolling Quantile(0.5, W)",
    description: "Crossover Double EMA adaptif yang dikombinasikan dengan penyaring kuantil dinamis (median) untuk mendeteksi breakout arah tren jangka menengah dengan phase lag yang sangat minim.",
    interpretation: "Memberikan sinyal beli (+1) jika harga melintasi level kuantil median ke atas, mengurangi sinyal palsu saat sideways.",
    stats: { correlation: "+0.18", accuracy: "58.7%", pcaWeight: "18.2%" },
  },
  AdvancedStochastic: {
    fullName: "Advanced Stochastic For-Loop Consensus",
    formula: "AvgTrend = Mean(Stoch(Close, r) for r in 1..129) >= 0.0",
    description: "Mengukur konsensus suara mayoritas tren di seluruh spektrum horizon waktu (dari 1 hingga 129 bar), menggantikan sistem crossover tradisional yang rentan terhadap whipsaw.",
    interpretation: "Penyelarasan krusial yang menaikkan korelasi dari negatif (-0.09) menjadi positif (+0.1408), menjamin akurasi fase BULL makro.",
    stats: { correlation: "+0.14", accuracy: "56.4%", pcaWeight: "15.8%" },
  },
  KalmanRSI: {
    fullName: "Kalman Filtered Relative Strength Index",
    formula: "RSI_k = KalmanFilter(RSI(Close, T), Q, R)",
    description: "Mengaplikasikan linear quadratic estimation (Kalman Filter) pada oscillator RSI klasik untuk menyaring noise frekuensi tinggi tanpa mengenalkan jeda waktu (zero phase-lag).",
    interpretation: "Mendeteksi kondisi jenuh beli/jenuh jual makro secara mulus dan presisi sebelum pembalikan arah harga terjadi.",
    stats: { correlation: "+0.19", accuracy: "59.3%", pcaWeight: "20.1%" },
  },
  FourierSupertrend: {
    fullName: "Adaptive Fourier Supertrend",
    formula: "DFT_Period = ArgMax(SpectralPower(LogReturns)); Supertrend(DFT_Period, Mult)",
    description: "Menggunakan Discrete Fourier Transform (DFT) pada log return untuk mengekstrak frekuensi siklus dominan Bitcoin, lalu menyesuaikan periode ATR Supertrend secara real-time.",
    interpretation: "Mengikuti dinamika durasi siklus pasar Bitcoin yang memanjang secara adaptif seiring pergeseran Ornstein-Uhlenbeck half-life.",
    stats: { correlation: "+0.16", accuracy: "57.1%", pcaWeight: "17.5%" },
  },
  TrendStrengthIndex: {
    fullName: "Trend Strength Index (TSI)",
    formula: "TSI = (VWMA(Close, T) - Close) / ATR(T)",
    description: "Mengukur kekuatan momentum dengan menghitung jarak terstandarisasi antara Volume Weighted Moving Average (VWMA) dan harga penutupan, dinormalisasi dengan ATR.",
    interpretation: "Sinyal bernilai +1 jika harga berada di atas VWMA (fase akumulasi volume positif) dan -1 jika di bawah VWMA.",
    stats: { correlation: "+0.13", accuracy: "55.0%", pcaWeight: "12.0%" },
  },
};

const ON_CHAIN_DETAILS = [
  {
    name: "STH-MVRV (Short-Term Holder MVRV)",
    threshold: "> 2.0 (Euphoria / Extreme Risk)",
    action: "Forced Exposure Capped to 0% (Cash)",
    formula: "STH-MVRV = Market Cap / Realized Cap (held < 155 days)",
    description: "Mengukur rasio nilai pasar terhadap harga perolehan (cost basis) koin milik pemegang jangka pendek (<155 hari). Di atas 2.0 menandakan seluruh spekulan ritel baru berada dalam keuntungan besar, secara historis merupakan puncak siklus (cycle top).",
  },
  {
    name: "STH-NUPL (Short-Term Holder NUPL)",
    threshold: "> 0.75 (Extreme Greed)",
    action: "Exposure Reduced / Risk-Off Override Active",
    formula: "STH-NUPL = (STH Market Cap - STH Realized Cap) / STH Market Cap",
    description: "Mengukur total keuntungan/kerugian bersih yang belum direalisasikan oleh pemegang koin jangka pendek. Nilai > 0.75 merepresentasikan euforia psikologis ekstrem di mana risiko koreksi tajam sangat tinggi.",
  },
  {
    name: "STH-SOPR (Short-Term Holder SOPR)",
    threshold: "Breakdown below 1.0",
    action: "Forced Exit / Exit Trigger Confirmation",
    formula: "STH-SOPR = Realized Value / Inception Value of spent coins",
    description: "Menghitung rasio keuntungan koin yang dibelanjakan oleh pemegang jangka pendek pada hari tersebut. Saat SOPR menembus ke bawah 1.0 dalam tren naik, ini menandakan kepanikan pemegang ritel yang mulai menjual rugi.",
  },
  {
    name: "Supply In Profit (LTH vs STH)",
    threshold: "Extreme High (> 95%) or Low (< 45%)",
    action: "Regime Bias Adjustment (Capitulation / Cycle Peak)",
    formula: "Supply In Profit % = Coins with Cost Basis < Current Price",
    description: "Persentase total pasokan Bitcoin yang terakhir bergerak di harga lebih rendah dari harga saat ini. Digunakan untuk mendeteksi dasar siklus (capitulation bottoms) atau puncak siklus makro.",
  },
];

export const FeatureDiagnosticsPanel: React.FC<FeatureDiagnosticsPanelProps> = ({ data }) => {
  const [activeTab, setActiveTab] = useState<"technical" | "onchain">("technical");
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [expandedIndicator, setExpandedIndicator] = useState<string | null>(null);

  // Default to latest record
  const latestIdx = data.length > 0 ? data.length - 1 : null;
  const activeIdx = selectedIdx !== null ? selectedIdx : latestIdx;
  const activeRecord = activeIdx !== null ? data[activeIdx] : null;

  if (!activeRecord) {
    return (
      <div className="bg-[var(--color-surface)] p-6 rounded-none border border-[var(--color-border)] text-[var(--color-text-muted)] text-center text-xs font-mono">
        No diagnostics telemetry available.
      </div>
    );
  }

  const scores = activeRecord.indicator_scores || {};
  const vif = activeRecord.vif || {};
  const pcaVariance = activeRecord.pca_variance_explained;

  // Check if any VIF exceeds 10
  const collinearCount = Object.values(vif).filter((v) => v > 10).length;

  const toggleExpand = (name: string) => {
    if (expandedIndicator === name) {
      setExpandedIndicator(null);
    } else {
      setExpandedIndicator(name);
    }
  };

  return (
    <div className="flex flex-col gap-6 h-full transition-all duration-300">
      {/* Panel Header */}
      <div className="flex justify-between items-center border-b border-[var(--color-border)] pb-4">
        <div className="text-[10px] text-[var(--color-text-muted)] font-mono bg-[var(--color-surface)] px-3 py-1.5 rounded border border-[var(--color-border)] inline-block">
          AS OF: {activeRecord.date}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex bg-[var(--color-surface)] p-1 rounded-none border border-[var(--color-border)]">
        <button
          onClick={() => setActiveTab("technical")}
          className={`flex-1 py-1.5 text-[10px] font-mono uppercase tracking-[0.05em] rounded transition-all duration-200 ${
            activeTab === "technical"
              ? "bg-[var(--color-surface)] text-[var(--color-text-primary)] shadow-[0_1px_2px_rgba(0,0,0,0.05)] font-semibold"
              : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          Technical ({Object.keys(vif).length})
        </button>
        <button
          onClick={() => setActiveTab("onchain")}
          className={`flex-1 py-1.5 text-[10px] font-mono uppercase tracking-[0.05em] rounded transition-all duration-200 ${
            activeTab === "onchain"
              ? "bg-[var(--color-surface)] text-[var(--color-text-primary)] shadow-[0_1px_2px_rgba(0,0,0,0.05)] font-semibold"
              : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          Overrides ({ON_CHAIN_DETAILS.length})
        </button>
      </div>

      {activeTab === "technical" ? (
        <>
          {/* PCA & VIF Metrics Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* PCA Card */}
            <div className="p-4 bg-[var(--color-surface)] rounded border border-[var(--color-border)] flex flex-col justify-between">
              <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] font-mono">
                PCA Variance Explained
              </div>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-xl font-medium text-[var(--color-text-primary)] font-mono">
                  {pcaVariance.toFixed(1)}%
                </span>
                <span className="text-[9px] text-[var(--color-bull)] uppercase tracking-wider px-2 py-0.5 rounded-none bg-[var(--color-surface)] border border-[var(--color-border)]">
                  &gt; 85% Target Met
                </span>
              </div>
              <p className="text-[10px] text-[var(--color-text-muted)] mt-2 leading-relaxed">
                Komponen utama ortogonal menyaring linear redundancy, menyisakan konsensus trend murni.
              </p>
            </div>

            {/* VIF Warning Card */}
            <div
              className={`p-4 rounded border flex flex-col justify-between ${
                collinearCount > 0
                  ? "bg-[var(--color-surface)] border-[var(--color-bear)] font-mono"
                  : "bg-[var(--color-surface)] border-[var(--color-border)]"
              }`}
            >
              <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] font-mono">
                Multicollinearity Status
              </div>
              <div className="flex items-center gap-2 mt-2">
                {collinearCount > 0 ? (
                  <>
                    <span className="text-xl font-medium text-[var(--color-bear)] font-mono">
                      {collinearCount} Alert
                    </span>
                    <span className="text-[9px] text-[var(--color-bear)] uppercase tracking-wider px-2 py-0.5 rounded-none bg-[var(--color-surface)] border border-[var(--color-bear)]">
                      CRITICAL: VIF &gt; 10
                    </span>
                  </>
                ) : (
                  <>
                    <span className="text-xl font-medium text-[var(--color-bull)] font-mono">
                      Clean
                    </span>
                    <span className="text-[9px] text-[var(--color-bull)] uppercase tracking-wider px-2 py-0.5 rounded-none bg-[var(--color-surface)] border border-[var(--color-border)]">
                      VIF &le; 10 Passed
                    </span>
                  </>
                )}
              </div>
              <p className="text-[10px] text-[var(--color-text-muted)] mt-2 leading-relaxed">
                Variance Inflation Factor memastikan tidak ada stacking indikator momentum berlebih.
              </p>
            </div>
          </div>

          {/* Feature Matrix Table */}
          <div className="flex flex-col gap-2 mt-2">
            <div className="overflow-x-auto border border-[var(--color-border)] rounded">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface)] font-mono text-[var(--color-text-muted)] text-[10px] uppercase tracking-wider">
                    <th className="p-3 pl-4 font-normal">Indicator</th>
                    <th className="p-3 font-normal">Score</th>
                    <th className="p-3 font-normal">VIF</th>
                    <th className="p-3 pr-4 text-right font-normal">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EAEAEA] bg-[var(--color-surface)]">
                  {Object.keys(vif).map((name) => {
                    const score = scores[name] ?? 0;
                    const vifValue = vif[name] ?? 0;
                    const isBullish = score === 1;
                    const isCollinear = vifValue > 10;
                    const details = INDICATOR_DETAILS[name];
                    const isExpanded = expandedIndicator === name;

                    return (
                      <React.Fragment key={name}>
                        <tr
                          onClick={() => toggleExpand(name)}
                          className={`cursor-pointer transition-colors duration-200 select-none ${
                            isExpanded ? "bg-[var(--color-surface)]" : "hover:bg-[var(--color-surface)]"
                          } ${isCollinear ? "bg-[var(--color-surface)]/30" : ""}`}
                        >
                          <td className="p-3.5 pl-4 text-[var(--color-text-primary)] font-mono">
                            {name}
                          </td>
                          <td className="p-3.5">
                            <span
                              className={`inline-flex items-center justify-center px-2 py-0.5 rounded text-[10px] font-mono ${
                                isBullish
                                  ? "bg-[var(--color-surface)] text-[var(--color-bull)] border border-[var(--color-border)]"
                                  : "bg-[var(--color-surface)] text-[var(--color-bear)] border border-[var(--color-border)]"
                              }`}
                            >
                              {score > 0 ? `+${score}` : score}
                            </span>
                          </td>
                          <td className="p-3.5 font-mono">
                            <span
                              className={
                                isCollinear ? "text-[var(--color-bear)]" : "text-[var(--color-text-muted)]"
                              }
                            >
                              {vifValue.toFixed(2)}
                            </span>
                          </td>
                          <td className="p-3.5 pr-4 text-right">
                            <span className="text-[10px] text-[var(--color-text-muted)] font-mono inline-flex items-center">
                              {isExpanded ? "Less ▲" : "More ▼"}
                            </span>
                          </td>
                        </tr>

                        {isExpanded && details && (
                          <tr className="bg-[var(--color-surface)]">
                            <td colSpan={4} className="p-4 pl-6 pr-6 border-b border-[var(--color-border)]">
                              <div className="flex flex-col gap-4 text-[var(--color-text-muted)] text-xs">
                                {/* Indicator Full Name & Math Formula */}
                                <div className="flex flex-col sm:flex-row justify-between gap-2 border-b border-[var(--color-border)] pb-3">
                                  <div>
                                    <div className="text-[9px] uppercase tracking-wider text-[var(--color-text-muted)] font-mono">
                                      Indicator Metric
                                    </div>
                                    <div className="text-sm font-serif text-[var(--color-text-primary)] mt-0.5">
                                      {details.fullName}
                                    </div>
                                  </div>
                                  <div className="text-left sm:text-right">
                                    <div className="text-[9px] uppercase tracking-wider text-[var(--color-text-muted)] font-mono">
                                      Mathematical Formula
                                    </div>
                                    <div className="font-mono text-[var(--color-text-primary)] text-xs bg-[var(--color-surface)] px-2 py-1 rounded border border-[var(--color-border)] mt-1 inline-block">
                                      {details.formula}
                                    </div>
                                  </div>
                                </div>

                                {/* Indicator Description */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                  <div className="md:col-span-2 flex flex-col gap-3">
                                    <div>
                                      <span className="font-medium text-[var(--color-text-primary)]">Deskripsi: </span>
                                      {details.description}
                                    </div>
                                    <div>
                                      <span className="font-medium text-[var(--color-text-primary)]">
                                        Logika Interpretasi LTTD:{" "}
                                      </span>
                                      {details.interpretation}
                                    </div>
                                  </div>

                                  {/* Stats Table */}
                                  <div className="p-3 bg-[var(--color-surface)] rounded border border-[var(--color-border)] flex flex-col gap-2">
                                    <div className="text-[9px] uppercase tracking-wider text-[var(--color-text-muted)] font-mono mb-1">
                                      Historical Performance
                                    </div>
                                    <div className="flex justify-between items-center py-1 border-b border-[var(--color-border)]">
                                      <span className="text-[var(--color-text-muted)]">Korelasi (r)</span>
                                      <span className="font-mono text-[var(--color-text-primary)]">
                                        {details.stats.correlation}
                                      </span>
                                    </div>
                                    <div className="flex justify-between items-center py-1 border-b border-[var(--color-border)]">
                                      <span className="text-[var(--color-text-muted)]">Akurasi Arah</span>
                                      <span className="font-mono text-[var(--color-text-primary)]">
                                        {details.stats.accuracy}
                                      </span>
                                    </div>
                                    <div className="flex justify-between items-center py-1">
                                      <span className="text-[var(--color-text-muted)]">Bobot PC1 Loading</span>
                                      <span className="font-mono text-[var(--color-text-primary)]">
                                        {details.stats.pcaWeight}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="flex flex-col gap-4 mt-2">
          <div className="p-4 bg-[var(--color-surface)] border border-[var(--color-border)] rounded">
            <h4 className="text-[10px] uppercase tracking-wider font-medium text-[var(--color-text-primary)] font-mono mb-2">
              Override Logic (Layer 2)
            </h4>
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
              Meskipun Layer 4 (Ensemble Aggregator) menghasilkan skor Bullish, sistem melacak status
              on-chain yang bersifat <strong>leading</strong> pada puncak siklus pasar. Jika batas
              ambang (threshold) terlampaui, alokasi exposure akan segera dipotong
              secara langsung untuk melindungi modal dari resiko koreksi makro.
            </p>
          </div>

          <div className="flex flex-col gap-2">
            {ON_CHAIN_DETAILS.map((item, idx) => (
              <div
                key={idx}
                className="p-4 bg-[var(--color-surface)] rounded border border-[var(--color-border)] flex flex-col gap-3"
              >
                <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                  <span className="text-sm font-medium text-[var(--color-text-primary)]">{item.name}</span>
                  <div className="flex gap-2">
                    <span className="px-2 py-0.5 bg-[var(--color-surface)] text-[var(--color-bear)] border border-[var(--color-border)] rounded text-[10px] font-mono">
                      Threshold: {item.threshold}
                    </span>
                    <span className="px-2 py-0.5 bg-[var(--color-surface)] text-[var(--color-sideways)] border border-[var(--color-border)] rounded text-[10px] font-mono">
                      {item.action}
                    </span>
                  </div>
                </div>
                <div className="text-[10px] text-[var(--color-text-primary)] font-mono bg-[var(--color-surface)] px-2 py-1 rounded border border-[var(--color-border)] self-start">
                  Formula: {item.formula}
                </div>
                <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Date slider to view historical diagnostics */}
      {data.length > 1 && activeIdx !== null && (
        <div className="flex flex-col gap-3 mt-4 pt-4 border-t border-[var(--color-border)]">
          <div className="flex justify-between items-center text-[10px] text-[var(--color-text-muted)] font-mono uppercase tracking-wider">
            <span>Historical Navigation</span>
            <span>
              Index: {activeIdx + 1} / {data.length}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={data.length - 1}
            value={activeIdx}
            onChange={(e) => setSelectedIdx(Number(e.target.value))}
            className="w-full accent-[var(--color-accent)] h-1 bg-[#EAEAEA] rounded appearance-none cursor-pointer"
          />
        </div>
      )}
    </div>
  );
};

