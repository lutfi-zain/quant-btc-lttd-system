import numpy as np
import pandas as pd
from src.features.importance import calculate_pratt_importance, rank_and_flag_features


def test_calculate_pratt_importance():
    np.random.seed(42)
    # y depends strongly on x1, weakly on x2, and not on x3
    x1 = np.random.randn(200)
    x2 = np.random.randn(200)
    x3 = np.random.randn(200)
    y = 3.0 * x1 + 0.3 * x2 + np.random.normal(0, 0.1, 200)

    df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3})
    pratt = calculate_pratt_importance(df, y)

    # Sum of Pratt's measures should be approximately 1.0 (explaining 100% of R^2)
    assert np.isclose(pratt.sum(), 1.0, atol=0.01)

    # x1 importance should be significantly larger than x2
    assert pratt["x1"] > pratt["x2"]
    
    # x3 importance should be near 0 (less than 0.01)
    assert pratt["x3"] < 0.01


def test_rank_and_flag_features():
    pratt_scores = pd.Series({
        "x1": 0.85,
        "x2": 0.14,
        "x3": 0.005,
        "x4": 0.005
    })

    report = rank_and_flag_features(pratt_scores)

    # check columns and shape
    assert report.shape == (4, 3)
    assert "pratt_measure" in report.columns
    assert "rank" in report.columns
    assert "flagged_for_removal" in report.columns

    # check ranking order
    assert report.index[0] == "x1"
    assert report.index[1] == "x2"
    assert report.iloc[0]["rank"] == 1
    assert report.iloc[1]["rank"] == 2

    # check flagging
    assert not report.loc["x1", "flagged_for_removal"]
    assert not report.loc["x2", "flagged_for_removal"]
    assert report.loc["x3", "flagged_for_removal"]
    assert report.loc["x4", "flagged_for_removal"]
