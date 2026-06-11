## ADDED Requirements

### Requirement: PCA Consensus Weighted Aggregation
Layer 4 Ensemble Aggregation mengimplementasikan PCA Consensus Weighted Aggregator (Option A) sebagai model default, yang menentukan bobot indikator teknikal dari absolute loadings pada Principal Component pertama (PC1).

#### Scenario: PCA Consensus Score Calculation
- **GIVEN** 6 indikator teknikal dengan loadings PC1 sebesar $v_1 = [0.4, -0.6, 0.2, 0.0, -0.4, 0.4]$
- **WHEN** skor arah indikator harian dihitung
- **THEN** bobot indikator ternormalisasi adalah $w = [0.2, 0.3, 0.1, 0.0, 0.2, 0.2]$ (sum = 1.0)
- **AND** final score $S_t$ dihitung sebagai weighted sum $\sum w_j \cdot I_{j,t}$ dan bernilai dalam rentang $[-1.0, +1.0]$.
