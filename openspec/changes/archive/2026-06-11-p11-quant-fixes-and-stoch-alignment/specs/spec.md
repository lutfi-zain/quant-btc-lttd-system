## ADDED Requirements

### Requirement: argmax-regime-classification
Market regime klasifikasi akhir setelah on-chain overrides harus ditentukan secara konsisten menggunakan Argmax murni (probabilitas posterior tertinggi) di pipeline daily run dan backtest runner, tanpa menyaring probabilitas BULL menggunakan batas threshold >0.70 yang heuristik.

#### Scenario: argmax-regime-selection
- **GIVEN** data posteriors dari HMM pasca on-chain overrides adalah `{"BULL": 0.51, "BEAR": 0.24, "SIDEWAYS": 0.25}`
- **WHEN** penentuan `final_regime` dieksekusi di pipeline atau backtest runner
- **THEN** `final_regime` harus ditetapkan sebagai `BULL` karena memiliki probabilitas tertinggi (Argmax), meskipun nilainya `<= 0.70`

#### Scenario: bear-override-argmax-selection
- **GIVEN** data posteriors awal dari HMM adalah `{"BULL": 0.80, "BEAR": 0.10, "SIDEWAYS": 0.10}` dan metrik `sth_mvrv` adalah `2.1` (memicu override bearish di mana P(BULL) dipaksa menjadi 0.0)
- **WHEN** penentuan `final_regime` dieksekusi setelah apply overrides
- **THEN** P(BULL) dipangkas ke 0.0, dan `final_regime` harus dipilih dari BEAR atau SIDEWAYS menggunakan Argmax, menghasilkan `BEAR` atau `SIDEWAYS` (tergantung mana yang lebih besar), bukan BULL

### Requirement: advanced-stochastic-reformulation
Indikator AdvancedStochastic harus dihitung sebagai trend-following indicator berbasis For-Loop multi-period statis 1..129 dengan smoothing %K SMA 21, dan menghasilkan korelasi positif dengan return Bitcoin 30 hari ke depan.

#### Scenario: stochastic-score-directionality
- **GIVEN** data close price Bitcoin berada dalam bull market kuat secara historis
- **WHEN** fungsi `compute()` dieksekusi untuk `AdvancedStochastic`
- **THEN** rata-rata arah tren dari 129 model stochastic (`avg`) harus dihitung, dan output `signals` bernilai `1.0` jika `avg >= 0.0`, dan `-1.0` jika `avg < 0.0`
- **AND** korelasi Pearson antara deret sinyal output `AdvancedStochastic` dengan `next_30d_return` harus bernilai positif ($r > 0.0$) pada dataset historis 2017–2025

## Non-Goals

1. Tidak ada perubahan pada batas threshold VIF pruning (tetap 10.0).
2. Tidak ada penambahan indikator teknis baru selain optimalisasi `AdvancedStochastic` yang sudah terdaftar.
