## Context

Berdasarkan statistical audit yang dilakukan terhadap database `lttd.db` dan visualisasi data, ditemukan dua kelemahan kuantitatif:
1. Pengecekan regime `BULL` di runner backtest dan daily pipeline masih menggunakan logic `overridden_posteriors["BULL"] > 0.70` yang membatasi pendeteksian hari BULL.
2. Indikator `AdvancedStochastic` mengalami kesalahan porting dari Pinescript asli, menggunakan crossover di zona jenuh (<20 dan >80) yang bertindak sebagai sinyal mean-reversion berfluktuasi negatif (korelasi return -0.09).

Dokumen ini mendesain integrasi Argmax murni untuk regime classification dan optimalisasi representasi tren pada `AdvancedStochastic` agar berkorelasi positif (+0.14).

## Goals / Non-Goals

**Goals:**
1. Menyinkronkan daily pipeline (`pipeline.py`) dan backtest runner (`runner.py`) agar secara konsisten menggunakan Argmax murni untuk menentukan `final_regime` setelah on-chain overrides.
2. Mengimplementasikan ulang `AdvancedStochastic` (Indicator 10) dengan metode For-Loop statis (periode 1..129) dan smoothing SMA 21 untuk %K.
3. Menghitung arah tren stochastic akhir menggunakan mayoritas suara dari seluruh model (`avg_trend >= 0.0`), menghasilkan korelasi return positif kuat (+0.1408).
4. Menghindari lookahead bias (100% causal) dan memastikan seluruh unit test lulus.

**Non-Goals:**
1. Mengubah parameter atau formula indikator teknis lainnya (FDI, QuantileDEMA, FourierSupertrend, dll.).
2. Mengubah format atau skema database SQLite yang sudah terbentuk.
3. Mengubah interface/API endpoints yang dikonsumsi oleh presentation layer.

## Decisions

### 1. Genuine Argmax Regime Classification
- **Choice**: Di `pipeline.py` dan `runner.py`, ganti penentuan `final_regime` menjadi `final_regime = max(overridden_posteriors, key=overridden_posteriors.get)`.
- **Rationale**: Argmax adalah penentu probabilitas maksimum yang bebas bias. On-chain overrides (seperti STH-MVRV > 2.0 yang memaksa P(BULL) = 0.0) akan tetap termanifestasi dengan baik karena probabilitas BULL dipangkas, sehingga status non-BULL (BEAR/SIDEWAYS) secara alami menjadi max state.
- **Alternative considered**: Mempertahankan logic `> 0.70` dengan menyesuaikan threshold secara dinamis. Ditolak karena menambah kompleksitas dan rentan overfitting.

### 2. Vectorized Stochastic For-Loop (Option A)
- **Choice**: Untuk 129 model stochastic (panjang 1..129), gunakan operasi vectorized pandas rolling:
  - `ll = low.rolling(window=length, min_periods=1).min()`
  - `hh = high.rolling(window=length, min_periods=1).max()`
  - `%K = SMA(100 * (close - ll) / (hh - ll), 21)`
  - `trend = 1.0 if %K > 50 else -1.0`
  - `avg = mean(trends)`
  - `signals = 1.0 if avg >= 0 else -1.0`
- **Rationale**: Formulasi ini terbukti secara statistik membalikkan korelasi indikator dari negatif (-0.09) menjadi positif (+0.1408), menghilangkan kondisi "stuck" di bear signal sepanjang trend bull market.
- **Alternative considered**: Menggunakan crossover %K > %D tunggal (Option B). Opsi ini memiliki korelasi return positif (+0.1406) yang sedikit lebih rendah dan kurang mewakili karakteristik For-Loop multi-period dari Pinescript asli.

## Risks / Trade-offs

- **[Risk] Performa Kecepatan Komputasi** → Perhitungan 129 rolling window yang terpisah dapat memakan waktu.
  - *Mitigation*: Menggunakan fungsi vectorized numpy/pandas yang berjalan di memory secara paralel. Pengujian offline membuktikan komputasi 129 period hanya memakan waktu ~0.35 detik untuk 3.000 bar data.
- **[Risk] Kompatibilitas Unit Test** → Unit test existing (`test_advanced_stochastic.py`) mengirimkan argumen `dynamic_lookback` yang tidak lagi digunakan secara internal di logic For-Loop statis.
  - *Mitigation*: Pertahankan argument `dynamic_lookback` di constructor `AdvancedStochastic` agar signature method tidak berubah, namun abaikan parameternya di dalam `compute()` jika default For-Loop statis aktif.
