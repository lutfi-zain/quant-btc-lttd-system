import pandas as pd
from src.backtest.runner import BacktestRunner

def test_backtest_runner_legacy_fixed_window():
    runner_legacy = BacktestRunner(legacy_fixed_window=True)
    res_legacy = runner_legacy.run(pd.DataFrame())
    assert res_legacy["legacy_fixed_window"] is True
    assert res_legacy["lookback"] == 200

    runner_dynamic = BacktestRunner(legacy_fixed_window=False)
    res_dynamic = runner_dynamic.run(pd.DataFrame())
    assert res_dynamic["legacy_fixed_window"] is False
    assert res_dynamic["lookback"] is None
