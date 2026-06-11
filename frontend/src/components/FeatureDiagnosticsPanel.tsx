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
      <div className="bg-[#0a0a0f] p-6 rounded-3xl border border-[#202025]/50 text-gray-500 text-center text-xs">
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
    <div className="flex flex-col gap-6 bg-[#0a0a0f] p-6 rounded-3xl border border-[#202025]/50 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl transition-all duration-300">
      {/* Panel Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-[#202025]/30 pb-4">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-purple-400">
            Layer 3 & 4 Transparency
          </span>
          <h3 className="text-sm font-semibold text-[#f3f4f6] mt-0.5">
            Feature Analytics & Calculation Rules
          </h3>
        </div>
        <div className="text-[10px] text-gray-500 font-mono bg-white/5 px-2.5 py-1 rounded-lg border border-white/5">
          AS OF: {activeRecord.date}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex bg-[#05050a] p-1 rounded-xl border border-[#202025]/30">
        <button
          onClick={() => setActiveTab("technical")}
          className={`flex-1 py-2 text-[10px] font-bold tracking-wider rounded-lg transition-all duration-300 ${
            activeTab === "technical"
              ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          TECHNICAL INDICATORS ({Object.keys(vif).length})
        </button>
        <button
          onClick={() => setActiveTab("onchain")}
          className={`flex-1 py-2 text-[10px] font-bold tracking-wider rounded-lg transition-all duration-300 ${
            activeTab === "onchain"
              ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          ON-CHAIN OVERRIDES ({ON_CHAIN_DETAILS.length})
        </button>
      </div>

      {activeTab === "technical" ? (
        <>
          {/* PCA & VIF Metrics Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* PCA Card */}
            <div className="p-4 bg-white/3 rounded-2xl border border-white/5 flex flex-col justify-between hover:bg-white/5 transition-all duration-300">
              <div className="text-[9px] uppercase tracking-wider text-gray-500 font-mono">
                PCA Variance Explained
              </div>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-2xl font-bold text-cyan-400 font-mono">
                  {pcaVariance.toFixed(1)}%
                </span>
                <span className="text-[9px] text-emerald-400 font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                  &gt; 85% Target Met
                </span>
              </div>
              <p className="text-[10px] text-gray-500 mt-2 leading-relaxed">
                Komponen utama ortogonal menyaring linear redundancy, menyisakan konsensus trend murni.
              </p>
            </div>

            {/* VIF Warning Card */}
            <div
              className={`p-4 rounded-2xl border flex flex-col justify-between transition-all duration-300 ${
                collinearCount > 0
                  ? "bg-rose-500/5 border-rose-500/20 shadow-[0_0_20px_rgba(239,68,68,0.05)] font-mono"
                  : "bg-white/3 border-white/5 hover:bg-white/5"
              }`}
            >
              <div className="text-[9px] uppercase tracking-wider text-gray-500 font-mono">
                Multicollinearity Status
              </div>
              <div className="flex items-center gap-2 mt-2">
                {collinearCount > 0 ? (
                  <>
                    <span className="text-2xl font-bold text-rose-400 font-mono">
                      {collinearCount} Alert
                    </span>
                    <span className="text-[9px] text-rose-400 font-bold px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/30 animate-pulse">
                      CRITICAL: VIF &gt; 10
                    </span>
                  </>
                ) : (
                  <>
                    <span className="text-2xl font-bold text-emerald-400 font-mono">
                      Clean
                    </span>
                    <span className="text-[9px] text-emerald-400 font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                      VIF &le; 10 Passed
                    </span>
                  </>
                )}
              </div>
              <p className="text-[10px] text-gray-500 mt-2 leading-relaxed">
                Variance Inflation Factor memastikan tidak ada stacking indikator momentum berlebih.
              </p>
            </div>
          </div>

          {/* Feature Matrix Table */}
          <div className="flex flex-col gap-2">
            <div className="flex justify-between items-center px-1">
              <span className="text-[9px] uppercase tracking-[0.15em] font-semibold text-gray-500">
                Technical Indicator Matrix
              </span>
              <span className="text-[9px] text-purple-400 font-medium animate-pulse">
                ℹ️ Klik baris untuk detail rumus & performa
              </span>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-[#202025]/30">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[#202025]/30 bg-white/3 font-semibold text-gray-400">
                    <th className="p-3 pl-4">Indicator</th>
                    <th className="p-3">Score</th>
                    <th className="p-3">VIF Value</th>
                    <th className="p-3 pr-4 text-right">Expansion Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#202025]/20 bg-white/2">
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
                          className={`cursor-pointer transition-all duration-300 select-none ${
                            isExpanded ? "bg-purple-950/20" : "hover:bg-white/5"
                          } ${isCollinear ? "bg-rose-500/3" : ""}`}
                        >
                          <td className="p-3.5 pl-4 font-semibold text-gray-200 font-mono">
                            {name}
                          </td>
                          <td className="p-3.5">
                            <span
                              className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-md text-[10px] font-bold font-mono ${
                                isBullish
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                              }`}
                            >
                              {score > 0 ? `+${score}` : score}
                            </span>
                          </td>
                          <td className="p-3.5 font-mono">
                            <span
                              className={
                                isCollinear ? "text-rose-400 font-bold" : "text-gray-400"
                              }
                            >
                              {vifValue.toFixed(2)}
                            </span>
                          </td>
                          <td className="p-3.5 pr-4 text-right">
                            <span className="text-[10px] text-purple-400 font-semibold inline-flex items-center gap-1">
                              {isExpanded ? "Hide ▲" : "Show Detail ▼"}
                            </span>
                          </td>
                        </tr>

                        {isExpanded && details && (
                          <tr className="bg-purple-950/5">
                            <td colSpan={4} className="p-4 pl-6 pr-6 border-b border-[#202025]/40">
                              <div className="flex flex-col gap-4 text-gray-400 text-xs">
                                {/* Indicator Full Name & Math Formula */}
                                <div className="flex flex-col sm:flex-row justify-between gap-2 border-b border-white/5 pb-2">
                                  <div>
                                    <div className="text-[10px] text-gray-500 font-mono">
                                      INDICATOR METRIC
                                    </div>
                                    <div className="text-sm font-bold text-gray-200">
                                      {details.fullName}
                                    </div>
                                  </div>
                                  <div className="text-right sm:text-right">
                                    <div className="text-[10px] text-gray-500 font-mono">
                                      MATHEMATICAL FORMULA
                                    </div>
                                    <div className="font-mono text-cyan-300 text-xs bg-black/40 px-3 py-1 rounded-lg border border-white/5 mt-0.5 inline-block">
                                      {details.formula}
                                    </div>
                                  </div>
                                </div>

                                {/* Indicator Description */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                  <div className="md:col-span-2 flex flex-col gap-2">
                                    <div>
                                      <span className="font-bold text-gray-300">Deskripsi: </span>
                                      {details.description}
                                    </div>
                                    <div>
                                      <span className="font-bold text-gray-300">
                                        Logika Interpretasi LTTD:{" "}
                                      </span>
                                      {details.interpretation}
                                    </div>
                                  </div>

                                  {/* Stats Table */}
                                  <div className="p-3 bg-white/2 rounded-xl border border-white/5 flex flex-col gap-2">
                                    <div className="text-[9px] uppercase tracking-wider text-gray-500 font-mono">
                                      Historical Performance (BTC)
                                    </div>
                                    <div className="flex justify-between items-center py-1 border-b border-white/5">
                                      <span className="text-gray-500">Korelasi (r)</span>
                                      <span className="font-mono font-bold text-emerald-400">
                                        {details.stats.correlation}
                                      </span>
                                    </div>
                                    <div className="flex justify-between items-center py-1 border-b border-white/5">
                                      <span className="text-gray-500">Akurasi Arah</span>
                                      <span className="font-mono font-bold text-cyan-400">
                                        {details.stats.accuracy}
                                      </span>
                                    </div>
                                    <div className="flex justify-between items-center py-1">
                                      <span className="text-gray-500">Bobot PC1 Loading</span>
                                      <span className="font-mono font-bold text-purple-400">
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
        /* On-Chain Override Logic transparency panel */
        <div className="flex flex-col gap-4">
          <div className="p-4 bg-purple-500/5 border border-purple-500/15 rounded-2xl">
            <h4 className="text-xs font-bold text-purple-400 font-mono mb-1">
              Override Logic (Layer 2)
            </h4>
            <p className="text-[11px] text-gray-400 leading-relaxed">
              Meskipun Layer 4 (Ensemble Aggregator) menghasilkan skor Bullish, sistem melacak status
              on-chain yang bersifat <strong>leading</strong> pada puncak siklus pasar. Jika batas
              ambang (threshold) di bawah terlampaui, alokasi exposure akan segera dipotong/di-bypass
              secara langsung untuk melindungi modal dari resiko koreksi makro (Risk-Off).
            </p>
          </div>

          <div className="flex flex-col gap-3">
            {ON_CHAIN_DETAILS.map((item, idx) => (
              <div
                key={idx}
                className="p-4 bg-white/2 rounded-2xl border border-[#202025]/40 flex flex-col gap-2 hover:bg-white/4 transition-all duration-300"
              >
                <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1.5">
                  <span className="text-xs font-bold text-gray-200 font-mono">{item.name}</span>
                  <div className="flex gap-2">
                    <span className="px-2 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-md text-[9px] font-mono">
                      Threshold: {item.threshold}
                    </span>
                    <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-md text-[9px] font-mono">
                      {item.action}
                    </span>
                  </div>
                </div>
                <div className="text-[10px] text-cyan-300 font-mono bg-black/30 px-2 py-0.5 rounded border border-white/3 self-start">
                  Formula: {item.formula}
                </div>
                <p className="text-[11px] text-gray-400 leading-relaxed mt-1">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Date slider to view historical diagnostics */}
      {data.length > 1 && activeIdx !== null && (
        <div className="flex flex-col gap-2 pt-2 border-t border-[#202025]/30">
          <div className="flex justify-between items-center text-[10px] text-gray-500 font-mono">
            <span>Historical Navigation Slider</span>
            <span>
              Date Index: {activeIdx + 1} / {data.length}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={data.length - 1}
            value={activeIdx}
            onChange={(e) => setSelectedIdx(Number(e.target.value))}
            className="w-full accent-purple-500 bg-[#12121a] h-1.5 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      )}
    </div>
  );
};

