## MODIFIED Requirements

### Requirement: Default ensemble is PCAConsensusEnsemble

The system SHALL use `PCAConsensusEnsemble` as the default ensemble model. `XGBoostEnsemble` SHALL be available as a fallback option but SHALL NOT be the default.

#### Scenario: Default ensemble selection

- **WHEN** the pipeline initializes the ensemble layer
- **THEN** the default ensemble SHALL be `PCAConsensusEnsemble`
- **AND** the ensemble SHALL compute `score = Σ |pc1_loading_i| × X[col_i]`

#### Scenario: XGBoost as fallback

- **WHEN** `ensemble_mode="xgboost"` is explicitly specified
- **THEN** the pipeline SHALL use `XGBoostEnsemble`
- **AND** `n_estimators` SHALL be reduced to 50 (from 300)

### Requirement: XGBoost objective fix

If `XGBoostEnsemble` is used, the objective function SHALL be `reg:squarederror` (not `reg:logistic`). The `scale_pos_weight` parameter SHALL be removed.

#### Scenario: XGBoost with correct objective

- **WHEN** `XGBoostEnsemble` is instantiated
- **THEN** `objective` SHALL be `"reg:squarederror"`
- **AND** `scale_pos_weight` SHALL NOT be set

#### Scenario: XGBoost without scale_pos_weight

- **WHEN** `XGBoostEnsemble` fits on continuous target `y ∈ [-1, 1]`
- **THEN** the model SHALL NOT use `scale_pos_weight`
- **AND** the loss function SHALL be appropriate for regression

### Requirement: PCAConsensusEnsemble input standardization

The `PCAConsensusEnsemble` SHALL apply StandardScaler to raw features before multiplying by PCA loadings. The scaler SHALL be fitted on training data only.

#### Scenario: Scaler fitting

- **WHEN** `PCAConsensusEnsemble.fit(X_train, pca_components, kept_cols)` is called
- **THEN** a `StandardScaler` SHALL be fitted on `X_train[kept_cols]`
- **AND** the scaler SHALL be stored for later use in prediction

#### Scenario: Scaler transformation

- **WHEN** `PCAConsensusEnsemble.predict(X_test)` is called
- **THEN** `X_test[kept_cols]` SHALL be transformed using the fitted scaler
- **AND** the scaled features SHALL be multiplied by PCA loadings

### Requirement: Ensemble removes QuantileDEMA

The ensemble SHALL NOT include QuantileDEMA in the feature matrix. QuantileDEMA SHALL be excluded from VIF analysis and PCA computation.

#### Scenario: QuantileDEMA excluded

- **WHEN** the feature matrix is constructed
- **THEN** the `quantile_dema` column SHALL NOT be present
- **AND** VIF analysis SHALL run on the remaining features only

#### Scenario: KalmanRSI excluded

- **WHEN** the feature matrix is constructed
- **THEN** the `kalman_rsi` column SHALL NOT be present
- **AND** only the reduced-lag version (RSI-50) SHALL be included

### Requirement: HMM posteriors as features

The ensemble SHALL include HMM posterior probabilities (`p_bull`, `p_bear`, `p_sideways`) as features in the ML model.

#### Scenario: HMM posteriors in feature matrix

- **WHEN** the feature matrix is constructed
- **THEN** columns `p_bull`, `p_bear`, `p_sideways` SHALL be present
- **AND** these values SHALL come from the HMM inference step

#### Scenario: HMM posteriors in ML training

- **WHEN** the ML ensemble is trained
- **THEN** the HMM posteriors SHALL be included in `X_train`
- **AND** the model SHALL learn weights for these features
