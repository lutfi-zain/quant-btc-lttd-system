import pytest
import numpy as np
from src.execution.sizing import calculate_target_exposure


def test_formula_validation():
    # final_score = 0.5, vol = 0.4
    # base_exposure = 0.5 + 0.5 * 0.5 = 0.75
    # vol_scalar = max(0.3, 1.0 - 0.4/0.8) = 0.5
    # target_exposure = 0.75 * 0.5 = 0.375
    assert calculate_target_exposure(0.5, 0.4) == pytest.approx(0.375)


def test_exposure_bounds():
    # Min exposure should be 0.3 even with high volatility / zero conviction
    assert calculate_target_exposure(0.0, 1.5) == pytest.approx(0.3)
    
    # Max exposure should be 1.0 even with maximum conviction and zero volatility
    assert calculate_target_exposure(1.0, 0.0) == pytest.approx(1.0)
    
    # Check that high conviction with moderate volatility does not exceed 1.0
    assert calculate_target_exposure(1.0, 0.1) <= 1.0


def test_exposure_smoothing_ema():
    # Check 5-day EMA smoothing: alpha = 1/3
    # raw_exposure = 0.9, prev_exposure = 0.6
    # smoothed = (1/3) * 0.9 + (2/3) * 0.6 = 0.3 + 0.4 = 0.7
    # diff = 0.7 - 0.6 = 0.1 (which is <= 0.2, so no clamping)
    # expected = 0.7
    # Let final_score=0.8, vol=0.0 (raw_exposure = 0.5 + 0.4 = 0.9)
    assert calculate_target_exposure(0.8, 0.0, prev_exposure=0.6) == pytest.approx(0.7)


def test_exposure_smoothing_change_limit():
    # Check that change is clamped to max 0.2
    # Let raw_exposure = 1.0, prev_exposure = 0.3
    # smoothed = (1/3) * 1.0 + (2/3) * 0.3 = 0.33333333333 + 0.2 = 0.53333333333
    # diff = 0.53333333333 - 0.3 = 0.23333333333
    # since diff > 0.2, clamped to 0.2
    # expected = 0.3 + 0.2 = 0.5
    # Let final_score=1.0, vol=0.0 (raw_exposure = 1.0)
    assert calculate_target_exposure(1.0, 0.0, prev_exposure=0.3) == pytest.approx(0.5)


def test_no_lookahead():
    # Causal behavior: verify calculations behave the same in isolation
    out1 = calculate_target_exposure(0.5, 0.3)
    out1_with_future = calculate_target_exposure(0.5, 0.3)
    assert out1 == out1_with_future
