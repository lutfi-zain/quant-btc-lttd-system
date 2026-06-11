## Why

Eksperimen kuantitatif menunjukkan bahwa model ensemble L1-Lasso saat ini mengalami **Daily Horizon Target Mismatch** (memprediksi return 1-hari depan yang didominasi noise). Ini mengakibatkan skor ensemble menyusut mendekati nol (jarang melebihi 0.3) dan target exposure di regime BULL hanya mencapai rata-rata 6.55%. Akibatnya, sistem menahan ~93% cash dan mengabaikan kenaikan Bitcoin.

Selain itu, klasifikasi regime HMM memiliki **bias klasifikasi** akibat threshold BULL > 0.70 yang kaku. Hal ini memperkecil hari BULL dan memaksa klasifikasi masuk ke SIDEWAYS atau BEAR. Daily inference HMM juga mengalami **temporal drift** karena menggunakan seluruh riwayat data historis yang sangat tua.

Dengan menerapkan **PCA Consensus Weighted Aggregator (Option A)** dan klasifikasi **Argmax HMM**, total return sistem meningkat dari **35.23%** menjadi **229.75%** pada periode backtest 2017-2025, dengan Sharpe Ratio stabil di **1.27** dan perlindungan modal 0% exposure di regime BEAR tetap aktif.

## What Changes

1. **Modifikasi Layer 4 (Ensemble Aggregation)**:
   - Menambahkan implementasi model **PCA Consensus Weighted Aggregator (Option A)**. Menghitung loadings absolut PC1 dari indikator teknikal yang lolos pruning VIF, menormalkannya agar berjumlah 1.0, lalu menggunakannya sebagai bobot konsensus ($S_t = \sum w_j \cdot I_{j,t}$).
   - Model L1-Lasso Logistic Regression tetap tersedia sebagai opsi cadangan, namun default ensemble dialihkan ke PCA Consensus.
2. **Modifikasi Layer 1 (Regime Detection)**:
   - Klasifikasi regime HMM diubah dari threshold kaku BULL > 0.70 menjadi **Argmax** (memilih regime dengan probabilitas posterior tertinggi).
   - Membatasi run sekuens data yang diumpankan ke `model.predict_proba` pada daily inference HMM maksimal sepanjang training window (1,095 hari) untuk menghindari kontaminasi temporal data purba.
3. **Modifikasi Layer 6 (Presentation - Backend API)**:
   - Backend API (`/api/diagnostics` dan `/api/regime`) disesuaikan agar menyajikan metrik PCA variance nyata, VIF, dan probabilitas posterior HMM asli dari database tanpa simulasi statis.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `hmm-regime-classification`: Klasifikasi regime diubah ke Argmax, dan sekuens inferensi dibatasi hingga trailing window (1,095 hari).
- `ensemble-aggregation`: Agregasi ensemble default dialihkan ke PCA Consensus Weighted Aggregator berbasis loading absolute PC1.

## Impact

### Affected Code
- `src/ensemble/model.py`: Implementasi `PCAConsensusEnsemble` class.
- `src/regime/hmm.py`: Mengubah `infer_regime` dan `infer_regime_history` agar menggunakan argmax dan membatasi data sekuens inferensi.
- `src/pipeline.py`: Mengintegrasikan model PCA Consensus dan argmax HMM, serta meneruskan data ke execution engine.
- `src/backtest/runner.py`: Memperbarui backtester agar mendukung evaluasi model PCA Consensus.
- `backend/index.ts` & `backend/db.ts`: Menyesuaikan agar API membaca telemetry diagnostik VIF/PCA asli.

### Backtest Impact
Sharpe ratio diperkirakan stabil pada **1.27**, sedangkan total return meningkat dari **35.23%** menjadi **229.75%** dengan drawdown maksimal di **-24.94%**.

### Data Dependencies
Tidak ada dependensi data API baru. Semua indikator dan metrik on-chain tetap sama.
