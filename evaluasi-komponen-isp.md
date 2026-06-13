# Evaluasi Komponen Sistem vs ISP (In-Sample Period)

**Dokumen Evaluasi Kuantitatif**
Target Evaluasi: `isp-regimes-btcusd-2026-06-12.csv`
Akurasi Pencocokan Kasar (HMM vs ISP): ~29.51% (18/61 transisi tepat waktu)

## 1. Layer 1: Deteksi Regime (HMM & On-Chain Filter)
**Bentuk Saat Ini (Shape):**
- Sistem menggunakan Gaussian HMM dengan **3 status (states)**: `BULL`, `BEAR`, dan `SIDEWAYS`.
- Filter *on-chain* (MVRV > 2.0 & NUPL > 0.75) diaplikasikan setelah *posterior probabilities* dari HMM keluar.

**Ketidaksesuaian dengan ISP:**
- **Miskalibrasi State:** ISP memiliki **5 status** (`Strong Bull`, `Weak Bull`, `Neutral`, `Weak Bear`, `Strong Bear`). HMM 3-status secara struktural *tidak mampu* merepresentasikan gradasi momentum (Strong vs Weak) secara langsung di level regime.
- **Lag (Kelambatan):** Evaluasi menunjukkan bahwa HMM (berbasis rolling volatility dan returns 21-hari) memiliki *lag* terhadap titik balik (turning points) yang didefinisikan dalam ISP. ISP tampaknya lebih ideal/melihat ke depan (*forward-looking* / annotated secara manual), sementara HMM berjalan ketat secara *causal* (tanpa bias masa depan).
- **Sensitivitas Filter Terlalu Kaku:** Syarat `STH-MVRV > 2.0` hampir tidak pernah tersentuh tepat di hari transisi ISP. Dari log eksekusi historis pada titik-titik transisi ISP, MVRV seringkali berada di range 1.0 - 1.6. Artinya, fitur "cycle top override" hampir tidak pernah bekerja saat ISP mendeklarasikan "Strong Bear".

**Rekomendasi (Actionable Steps):**
- Mengubah struktur Layer 1 untuk fokus pada penentuan *bias* makro (Bull/Bear), lalu memanfaatkan Layer 4 (Ensemble Score) untuk mendeduksi tingkat "Strong" atau "Weak".
- Menurunkan ambang batas (*threshold*) dari filter on-chain, atau menggunakan pendekatan probabilistik/skalar alih-alih override keras `0.0`.

## 2. Layer 2 & 3: Signal Engine & Feature Processing
**Bentuk Saat Ini (Shape):**
- 6 Indikator teknikal kausal (FDI, Quantile DEMA, Kalman RSI, dll).
- Reduksi multikolinearitas dengan VIF (< 10) dan PCA (*Principal Component Analysis*).

**Kinerja:**
- Secara statistik, komponen ini sudah sangat tangguh untuk membuang *noise* dan mencegah *lookahead bias* yang dilarang keras di `AGENTS.md`.
- Namun, output dari indikator-indikator ini dikompresi menjadi `-1.0` hingga `+1.0`. Karena target ISP berbentuk diskrit (5 status), hasil PCA ini harus dipetakan kembali dengan lebih sensitif agar sejalan dengan definisi `Strong/Weak` di ISP.

## 3. Layer 4: Ensemble Aggregation
**Bentuk Saat Ini (Shape):**
- Menggunakan pendekatan koefisien PCA (`PCAConsensusEnsemble`) atau Lasso L1-Logistic Regression untuk menggabungkan indikator.
- Model memprediksi "Final Score" (probabilitas untung/naik di bar berikutnya).

**Ketidaksesuaian dengan ISP:**
- Target yang dilatih pada model adalah sekadar naik/turunnya harga pada hari berikutnya (`np.sign(price_diff)`). Model *tidak* dilatih untuk memprediksi "Weak" vs "Strong" regime dari ISP.

## 4. Layer 5: Execution Engine (Sizing)
**Bentuk Saat Ini (Shape):**
```python
if reg == "BEAR": return 0.0
elif reg == "BULL": return max(0.0, min(1.0, final_score))
elif reg == "SIDEWAYS": return max(0.0, min(0.5, final_score))
```

**Ketidaksesuaian dengan ISP:**
- ISP membedakan `Weak Bear` (mungkin masih butuh eksposur kecil atau short yang kecil) dan `Strong Bear` (eksposur 0). Di sistem saat ini, **semua** bentuk BEAR langsung di-_flatten_ menjadi exposure `0.0`.
- ISP mencatat `Neutral`, sementara sistem meng-_cap_ `SIDEWAYS` di `0.5` maksimal, tidak peduli seberapa kuat `final_score`.

---

## Kesimpulan Evaluasi Kinerja (Performance)

Akurasi keselarasan waktu yang rendah (29.5%) antara eksekusi HMM real-time vs titik-titik ISP terjadi karena **ISP adalah Ground Truth (Annotated Path)**, sedangkan sistem kuantitatif dipaksa menggunakan data masa lalu (causal 100%) dengan *lagging indicators*.

**Sistem saat ini TIDAK didesain untuk mereplika persis kelima status ISP secara kategorikal.**

### Proposal Solusi Resolusi (Pilih Salah Satu):

1. **Opsi A: Mapping 5-State Sizing (Menyesuaikan Sistem ke ISP)**
   Ubah Layer 5 (`sizing.py`) agar menafsirkan gabungan `Regime (3 states)` + `Final Score (-1 to 1)` ke dalam 5 status ISP:
   - `Regime = BULL, Score > 0.5` -> **Strong Bull**
   - `Regime = BULL, Score <= 0.5` -> **Weak Bull**
   - `Regime = SIDEWAYS` -> **Neutral**
   - `Regime = BEAR, Score > -0.5` -> **Weak Bear**
   - `Regime = BEAR, Score <= -0.5` -> **Strong Bear**

2. **Opsi B: Retrain HMM Menjadi 5-State**
   Mengubah `n_components=5` pada HMM di `hmm.py`, namun ini berisiko melanggar prinsip *stability* yang ditemukan di riset sebelumnya karena data Bitcoin terlalu berisik (noisy) untuk membagi kluster ke dalam 5 status tanpa *overfitting*.
