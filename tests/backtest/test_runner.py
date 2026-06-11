import numpy as np
import pandas as pd
import pytest
from src.backtest.runner import BacktestRunner, MockExecutionAdapter


def test_mock_execution_adapter():
    adapter = MockExecutionAdapter()
    
    # 1. First record (no transition should be logged since previous_regime is None)
    res1 = adapter.run("2026-01-01", 0.5, "BULL", {"BULL": 0.8, "BEAR": 0.1, "SIDEWAYS": 0.1})
    assert res1["target_exposure"] == 0.5
    assert res1["regime"] == "BULL"
    assert res1["transition_occurred"] is False
    assert len(adapter.transitions) == 0
    
    # 2. Second record (transition from BULL to BEAR)
    res2 = adapter.run("2026-01-02", -0.2, "BEAR", {"BULL": 0.0, "BEAR": 0.9, "SIDEWAYS": 0.1})
    assert res2["target_exposure"] == 0.0
    assert res2["regime"] == "BEAR"
    assert res2["transition_occurred"] is True
    assert len(adapter.transitions) == 1
    assert adapter.transitions[0]["from_regime"] == "BULL"
    assert adapter.transitions[0]["to_regime"] == "BEAR"
    
    # 3. Retrieve dataframe
    df = adapter.get_dataframe()
    assert len(df) == 2
    assert "target_exposure" in df.columns
    assert "regime" in df.columns


def test_backtest_runner_e2e():
    # Generate mock OHLCV + Onchain data (1600 days to support WFO sliding window)
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=1600, freq="D")
    
    # Random walk for close prices
    closes = np.cumsum(np.random.normal(0.0005, 0.01, 1600)) + 100.0
    highs = closes + np.random.uniform(0.1, 1.0, 1600)
    lows = closes - np.random.uniform(0.1, 1.0, 1600)
    opens = (highs + lows) / 2.0
    volumes = np.random.uniform(100, 1000, 1600)
    
    # Onchain metrics
    sth_mvrv = np.random.uniform(1.0, 1.8, 1600)
    sth_nupl = np.random.uniform(0.1, 0.6, 1600)
    sth_sopr_24h = np.random.uniform(0.98, 1.02, 1600)
    sth_supply_in_profit = np.random.uniform(0.6, 0.9, 1600)
    
    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "sth_mvrv": sth_mvrv,
        "sth_nupl": sth_nupl,
        "sth_sopr_24h": sth_sopr_24h,
        "sth_supply_in_profit": sth_supply_in_profit,
        "stamp": dates  # For point-in-time join column
    }, index=dates)
    
    # Run dynamic lookback runner
    runner = BacktestRunner(legacy_fixed_window=False)
    res = runner.run(df)
    
    assert res["status"] == "success"
    assert "metrics" in res
    assert "total_return" in res["metrics"]
    assert "annualized_sharpe" in res["metrics"]
    assert "max_drawdown" in res["metrics"]
    assert "regime_metrics" in res["metrics"]
    
    # Validate result dataframe
    results_df = res["results"]
    assert len(results_df) > 0
    assert "target_exposure" in results_df.columns
    assert "regime" in results_df.columns
    assert "final_score" in results_df.columns
    
    # Validate value constraints
    assert (results_df["target_exposure"] >= 0.0).all()
    assert (results_df["target_exposure"] <= 1.0).all()
    
    # Run legacy fixed window runner
    runner_legacy = BacktestRunner(legacy_fixed_window=True)
    res_legacy = runner_legacy.run(df)
    assert res_legacy["status"] == "success"
    assert res_legacy["legacy_fixed_window"] is True
