import pytest
import numpy as np
from src.execution.sizing import calculate_target_exposure

def test_formula_validation():
    # SIDEWAYS
    # score=0.5 -> conviction = 0.75
    # raw_exposure = 0.75 * 2.0 = 1.5
    # no vol dampener since 0.02*19.1 < 1.0
    # prev_exposure=0.0 -> returns raw_exposure
    assert calculate_target_exposure(0.5, 0.02, regime="SIDEWAYS") == pytest.approx(1.5)

def test_exposure_bounds():
    # BEAR = 0.0
    assert calculate_target_exposure(1.0, 0.02, regime="BEAR") == pytest.approx(0.0)

    # SIDEWAYS high conviction (score=1.0 -> conv=1.0 -> raw=2.0)
    # prev_exposure=2.0 -> returns 2.0
    assert calculate_target_exposure(1.0, 0.02, regime="SIDEWAYS", prev_exposure=2.0) == pytest.approx(2.0)

    # BULL high conviction (score=1.0 -> conv=1.0 -> raw=1.0+1.5 = 2.5)
    assert calculate_target_exposure(1.0, 0.02, regime="BULL", prev_exposure=2.5) == pytest.approx(2.5)

def test_exposure_smoothing_ema():
    # SIDEWAYS:
    # score=0.8 -> conviction=0.5 + 0.4 = 0.9
    # raw = 0.9 * 2.0 = 1.8
    # smoothed = 1/3 * 1.8 + 2/3 * 0.6 = 0.6 + 0.4 = 1.0
    assert calculate_target_exposure(0.8, 0.02, prev_exposure=0.6, regime="SIDEWAYS") == pytest.approx(0.9)

def test_exposure_smoothing_change_limit():
    # Change max is 0.3
    # BULL: score=1.0 -> conviction=1.0 -> raw=2.5
    # prev=0.3
    # smoothed = 1/3 * 2.5 + 2/3 * 0.3 = 0.8333 + 0.2 = 1.0333
    # diff = 1.0333 - 0.3 = 0.7333 (exceeds 0.3 clamp)
    # final = 0.3 + 0.3 = 0.6
    assert calculate_target_exposure(1.0, 0.02, prev_exposure=0.3, regime="BULL") == pytest.approx(0.6)

def test_no_lookahead():
    out1 = calculate_target_exposure(0.5, 0.02, regime="BULL")
    out1_with_future = calculate_target_exposure(0.5, 0.02, regime="BULL")
    assert out1 == out1_with_future
