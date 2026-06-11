## ADDED Requirements

### Requirement: HMM Classification to Argmax
Klasifikasi regime HMM diubah dari threshold statis BULL > 0.70 menjadi model argmax murni berdasarkan probabilitas posterior terbesar untuk menghindari bias pemilihan regime.

#### Scenario: HMM Classification using Argmax
- **GIVEN** model Gaussian HMM terlatih dengan state-to-regime mapping
- **WHEN** probabilitas posterior hari $t$ adalah $P(\text{Bull}) = 0.65$, $P(\text{Bear}) = 0.15$, dan $P(\text{Sideways}) = 0.20$
- **THEN** regime terpilih harus diidentifikasi sebagai BULL (karena BULL memiliki probabilitas posterior tertinggi).

### Requirement: Inference Context Bounding
Untuk menghindari drift temporal akibat sekuens data yang terlalu panjang, run data harga close yang diberikan ke `predict_proba` saat daily inference HMM dipotong maksimal sepanjang training window (1,095 hari).

#### Scenario: Trailing Window Sequence Bounding
- **GIVEN** data harga close historis sepanjang 4,500 hari
- **WHEN** daily inference HMM dijalankan pada hari $t$
- **THEN** panjang input array fitur yang masuk ke `predict_proba` maksimal berukuran 1,095 data point penutup (trailing).
