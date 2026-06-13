# XGBoost Engine Builder Plan

## Goal
Achieve Sharpe > 1.8 and CAGR > 80% using non-linear tree ensembles (XGBoost/LightGBM/RandomForest).

## Current State
- The ML consensus (L1 Lasso) only achieves ~0.7 Sharpe and 120% CAGR, with weak predictive edge in the middle score range (0.4 - 0.7).
- Binary sizing fails because the edge is weak. We need an XGBoost model that can confidently classify the state with high probability and accuracy.

## Step 1: Feature Engineering
- Expand `FeatureMatrixBuilder` in `src/features/builder.py`.
- Add raw on-chain metrics (not just ROC).
- Add multi-horizon price momentum (returns over 1d, 3d, 7d, 14d, 30d, 90d, 180d, 350d).
- Add multi-horizon volatility.
- Add moving average distances (price / SMA(N) for N in [20, 50, 100, 200]).

## Step 2: Implement XGBoost Model
- Create `src/ensemble/xgboost_model.py`.
- Implement `XGBoostEnsemble` class with WFO compatibilities.
- Use `binary:logistic` objective to predict probability of uptrend.
- Add hyperparameter tuning or regularization to prevent overfitting on the noisy BTC data.
- Ensure the output can be parsed by `predict_score()` as continuous probabilities for sizing logic, or use binary if the hit-rate improves.

## Step 3: WFO Integration & Backtesting
- Update `src/backtest/runner.py` to accept `--ensemble-mode xgboost`.
- Run WFO backtest.

## Step 4: Iteration
- Analyze feature importance using XGBoost's built-in feature importances.
- Drop useless features.
- Tune XGBoost parameters (max_depth, learning_rate, subsample, colsample_bytree) to maximize Walk-Forward OOS Sharpe.
