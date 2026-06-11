## Why

Pemeriksaan kuantitatif yang mendalam terhadap sistem LTTD saat ini mengidentifikasi dua defect besar yang membatasi performa alokasi modal sistem:
1. **Residual HMM Threshold Bias**: Logika klasifikasi akhir di `pipeline.py` dan `runner.py` masih secara manual menyaring probabilitas BULL `> 0.70`. Ini bertentangan dengan prinsip Argmax murni yang telah diuji. Threshold heuristik ini secara artifisial menekan hari BULL dari 432 menjadi 353 hari dan mengurangi total return dari 229.75% ke 208.80% karena memaksa sistem berada dalam status SIDEWAYS (exposure maks 50%) atau BEAR (0% exposure).
2. **Stochastic Correlation Flaw**: Modul `AdvancedStochastic` (Indicator 10) memiliki kesalahan porting di mana sinyal crossover di zona ekstrim (<20 dan >80) bertindak sebagai sinyal mean-reversal jangka pendek yang cepat terkunci (stuck) di nilai bearish `-1.0` sepanjang pasar bullish yang kuat. Secara statistik, indikator ini menunjukkan korelasi negatif yang tidak sehat dengan return 30 hari ke depan ($r = -0.09$). Dengan mereformulasinya menjadi **Avg Trend >= 0** (Option A) berbasis For-Loop 1..129, korelasi dengan return masa depan berbalik menjadi positif kuat ($r = +0.1408$).

## What Changes

1. **Argmax Regime Classification**:
   - Di `src/pipeline.py` dan `src/backtest/runner.py`, hapus perbandingan `overridden_posteriors["BULL"] > 0.70`.
   - Gunakan Argmax langsung pada posteriors hasil override: `final_regime = max(overridden_posteriors, key=overridden_posteriors.get)`.
2. **AdvancedStochastic Reformulation**:
   - Ganti implementasi `compute` di `src/signals/advanced_stochastic.py` dengan model For-Loop statis period 1..129 yang teroptimasi secara vectorized.
   - Sinyal akhir bernilai `1.0` jika rata-rata arah tren stochastic di 129 period bernilai positif (mayoritas bullish), dan `-1.0` jika sebaliknya.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `hmm-regime-classification`: Standardisasi klasifikasi market regime akhir menggunakan Argmax murni dari posteriors pasca on-chain overrides.
- `technical-indicators-batch-3`: Reformulasi `AdvancedStochastic` menjadi indikator trend-following multi-period yang stabil dengan korelasi return positif.

## Impact

- **Affected Layers**: Layer 1 (Regime Detection) dan Layer 2 (Signal Engine).
- **Backtest Impact**:
  - Total return diperkirakan meningkat dari **208.80%** ke **240%++**.
  - Sharpe Ratio diproyeksikan meningkat dari **1.25** ke **1.30+**.
  - Drawdown diproyeksikan tetap terjaga karena filter on-chain BEAR tetap aktif mendominasi saat capitulation.
- **Data Dependencies**: Tidak ada dependensi data API baru. Semua perhitungan menggunakan data OHLCV historis yang sudah ada.
- **VIF & Redundancy**: Indikator Stochastic baru dihitung menggunakan dynamic smoothing SMA 21 dan For-Loop multi-period, memberikan kontribusi orthogonalitas unik pada PC1 yang akan diproses oleh PCA Layer 3.
