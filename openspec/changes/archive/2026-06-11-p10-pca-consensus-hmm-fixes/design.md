## Context

LTTD Trading System saat ini menggunakan model ensemble L1-Lasso Logistic Regression (Layer 4) yang melatih prediksi arah pergerakan harga 1-hari ke depan. Hal ini melanggar "intended macro horizon" sistem (120-350 hari) karena model mendeteksi *noise* harian yang dominan. Hasilnya, probabilitas model terkompresi kuat di sekitar $0.5$, membatasi target exposure maksimal hanya $\approx 26\%$ saat BULL, dan menahan sistem $\approx 93\%$ di cash. 

Klasifikasi HMM (Layer 1) juga dibatasi oleh threshold BULL > 0.70 statis yang bias, dan daily inference-nya menggunakan seluruh barisan data historis dari 2016 sehingga mengalami kerentanan terhadap drift historis (*sequence history contamination*). 

## Goals / Non-Goals

**Goals:**
- Mengimplementasikan model **PCA Consensus Weighted Aggregator (Option A)** sebagai metode agregasi Layer 4 untuk menghasilkan skor konsensus tren yang tidak tertekan noise harian.
- Mengubah klasifikasi HMM ke **Argmax** (mengambil probabilitas posterior tertinggi) untuk mengeliminasi bias threshold.
- Membatasi panjang sekuens inferensi HMM maksimal sepanjang training window (1,095 hari) untuk mencegah kontaminasi drift data masa lalu.
- Memastikan database menyimpan metrics nyata untuk VIF dan PCA variance, serta HMM posterior lengkap, agar API Backend dapat menyajikan data telemetri yang valid tanpa manipulasi simulasi statis di Layer 6.
- Memastikan semua pengujian unit (`pytest`) dan backtest tetap causal tanpa lookahead bias.

**Non-Goals:**
- Membuat indikator teknikal baru di Layer 2 (menggunakan 6 indikator teknikal yang sudah ada: FDI, QuantileDEMA, AdvancedStochastic, KalmanRSI, FourierSupertrend, TrendStrengthIndex).
- Mengubah model klasifikasi L1-Lasso (Lasso tetap dipertahankan di codebase sebagai pembanding atau opsi alternatif).

## Decisions

### 1. Struktur PCAConsensusEnsemble
- **Pilihan**: Membuat kelas `PCAConsensusEnsemble` di `src/ensemble/model.py` yang menerima loadings dari `CausalPCA` di Layer 3.
- **Rasional**: Loading PC1 merepresentasikan arah kesepakatan variansi dominan dari 6 indikator teknikal. Dengan menormalkan nilai absolut dari loading PC1, kita mendapatkan bobot penjumlahan $w_j$ yang independen terhadap model fitting berisik (noise).
- **Alternatif**: Menggunakan rata-rata indikator secara langsung (Equal Weight). Pilihan ini ditolak karena equal weight mengabaikan fakta bahwa beberapa indikator lebih collinear daripada yang lain, sedangkan PCA Consensus secara alami mengoreksi collinearity dengan memberikan bobot lebih kecil pada indikator redundan.

### 2. Klasifikasi HMM Menggunakan Argmax
- **Pilihan**: Menghapus threshold BULL > 0.70 statis pada file `src/regime/hmm.py` dan `src/pipeline.py` dan menggunakan `max(posteriors, key=posteriors.get)`.
- **Rasional**: Memastikan klasifikasi regime objektif mengikuti distribusi probabilitas posterior yang paling dominan.
- **Alternatif**: Menurunkan threshold BULL menjadi 0.50 atau 0.60. Pilihan ini ditolak karena angka threshold tersebut tetaplah nilai heuristik yang arbitrer. Argmax adalah standar klasifikasi model probabilitas.

### 3. Pembatasan Sekuens Inferensi HMM
- **Pilihan**: Memotong sekuens input harga close pada `infer_regime` maksimal sepanjang 1,095 hari trailing (3 tahun).
- **Rasional**: Ini menyelaraskan konteks inferensi HMM dengan konteks training HMM yang dilakukan pada 1,095 hari. Hal ini mencegah error akumulasi probabilitas transisi yang disebabkan oleh rentang waktu 10+ tahun.

### 4. Penyimpanan Diagnostik Nyata di SQLite
- **Pilihan**: Memperluas tabel atau kolom di database jika diperlukan, atau mengintegrasikan kalkulasi diagnostik yang presisi ke dalam pipeline agar disimpan langsung ke SQLite.
- **Rasional**: Memungkinkan Backend API `/api/diagnostics` dan `/api/regime` menyajikan data telemetri VIF dan PCA nyata dari database tanpa perlu *hardcoded simulations* (seperti AdvancedStochastic VIF = 11.24 konstan).

## Risks / Trade-offs

- **[Risk]** Peningkatan volatilitas posisi akibat target exposure yang bisa menyentuh 100% (dibanding baseline 26%).
  - *Mitigation*: Regime BEAR tetap memegang 0% exposure (capital preservation). HMM dan on-chain overrides (STH-MVRV > 2.0 dan STH-NUPL > 0.75) bertindak sebagai saringan pelindung utama untuk menekan exposure ke 0% atau maksimal 50% saat gelembung harga/kapitulasi terjadi.
- **[Risk]** PCA components axis flipping (tanda PC1 berbalik arah).
  - *Mitigation*: Memanfaatkan fungsi `sign-alignment` di `CausalPCA` yang menyelaraskan tanda PC1 dengan arah mean indikator secara konsisten.
