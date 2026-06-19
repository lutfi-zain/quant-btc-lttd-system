import pandas as pd
from src.signals.base import CausalFilter


def test_no_lookahead(indicator: CausalFilter, data: pd.DataFrame, t_index: int):
    """
    Verify that appending future bars does not alter the historical Indicator Score
    computed at bar t.

    Args:
        indicator (CausalFilter): The indicator to test.
        data (pd.DataFrame): The full dataset including future bars (up to t+N).
        t_index (int): The integer index representing the current bar `t`.
    """
    # Truncated data up to t
    truncated_data = data.iloc[: t_index + 1].copy()

    score_truncated = indicator.compute(truncated_data)
    val_truncated = score_truncated.iloc[-1]

    # Full extended data
    score_full = indicator.compute(data)
    val_full = score_full.iloc[t_index]

    if pd.isna(val_truncated) and pd.isna(val_full):
        return

    import numpy as np
    assert np.isclose(val_truncated, val_full, rtol=1e-9, atol=1e-9), (
        f"Lookahead bias detected! Value at t={t_index} changed from {val_truncated} to {val_full} when future data was added."
    )


test_no_lookahead.__test__ = False
