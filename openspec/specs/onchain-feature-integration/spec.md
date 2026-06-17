# onchain-feature-integration Specification

## Purpose
TBD - created by archiving change fix-lttd-system. Update Purpose after archive.

## Requirements

### Requirement: On-chain metrics in feature matrix

The system SHALL include STH-MVRV, STH-NUPL, STH-SOPR, and STH-SupplyInProfit as columns in the ML feature matrix. These metrics SHALL be fetched from BRK API and merged with OHLCV data by date.

#### Scenario: On-chain features present in feature matrix

- **WHEN** `FeatureMatrixBuilder.build_matrix()` is called
- **THEN** the output DataFrame SHALL contain columns: `sth_mvrv`, `sth_nupl`, `sth_sopr_24h`, `sth_supply_in_profit`
- **AND** these columns SHALL be aligned with the OHLCV data by date index

#### Scenario: On-chain feature values are raw

- **WHEN** on-chain metrics are added to the feature matrix
- **THEN** the values SHALL be the raw metric values from BRK API
- **AND** NO additional transformation (z-score, normalization) SHALL be applied before PCA

### Requirement: On-chain freshness validation

The system SHALL validate that on-chain metrics are fresh before including them in the feature matrix. The BRK `stamp` field SHALL be >= yesterday's date.

#### Scenario: Fresh on-chain data

- **WHEN** the pipeline fetches on-chain metrics from BRK
- **AND** the `stamp` field in the response >= yesterday
- **THEN** the on-chain metrics SHALL be included in the feature matrix

#### Scenario: Stale on-chain data

- **WHEN** the pipeline fetches on-chain metrics from BRK
- **AND** the `stamp` field in the response < yesterday
- **THEN** the pipeline SHALL raise `DataStaleException`
- **AND** the on-chain metrics SHALL NOT be included in the feature matrix

### Requirement: On-chain metrics passed to ML ensemble

The on-chain features SHALL be included in the input to the ML ensemble (PCAConsensusEnsemble or XGBoost). They SHALL NOT be used only for HMM posterior overrides.

#### Scenario: On-chain in ML training

- **WHEN** the ML ensemble is trained on `X_train`
- **THEN** `X_train` SHALL contain on-chain feature columns
- **AND** the ensemble model SHALL learn weights for these features

#### Scenario: On-chain in ML prediction

- **WHEN** the ML ensemble predicts on `X_test`
- **THEN** `X_test` SHALL contain on-chain feature columns
- **AND** the prediction SHALL incorporate on-chain information

### Requirement: VIF analysis includes on-chain metrics

The VIF pruning step SHALL include on-chain metrics in its analysis. On-chain metrics with VIF > 10 SHALL be flagged for review.

#### Scenario: On-chain VIF check

- **WHEN** VIF analysis runs on the feature matrix
- **THEN** on-chain metrics SHALL be included in the VIF calculation
- **AND** any on-chain metric with VIF > 10 SHALL be reported in the diagnostics

### Requirement: Feature matrix builder includes on-chain columns

The `FeatureMatrixBuilder.build_matrix()` method SHALL accept an optional `onchain_df` parameter containing on-chain metrics. When provided, these metrics SHALL be added as columns to the output.

#### Scenario: Build matrix with on-chain

- **WHEN** `build_matrix(df_merged, onchain_df=onchain_data)` is called
- **THEN** the output SHALL contain both technical indicator columns and on-chain columns
- **AND** the index SHALL be the same as the input `df_merged`

#### Scenario: Build matrix without on-chain (backward compatible)

- **WHEN** `build_matrix(df_merged)` is called without `onchain_df`
- **THEN** the output SHALL contain only technical indicator columns
- **AND** the behavior SHALL be identical to the current implementation
