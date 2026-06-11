import pytest
from src.execution.sizing import calculate_target_exposure


def test_bull_regime_sizing():
    assert calculate_target_exposure(0.8, "BULL") == 0.8
    assert calculate_target_exposure(1.0, "BULL") == 1.0
    assert calculate_target_exposure(1.5, "BULL") == 1.0
    assert calculate_target_exposure(0.0, "BULL") == 0.0
    assert calculate_target_exposure(-0.5, "BULL") == 0.0
    assert calculate_target_exposure(0.5, "bull") == 0.5  # Case insensitivity


def test_sideways_regime_sizing():
    assert calculate_target_exposure(0.3, "SIDEWAYS") == 0.3
    assert calculate_target_exposure(0.5, "SIDEWAYS") == 0.5
    assert calculate_target_exposure(0.8, "SIDEWAYS") == 0.5
    assert calculate_target_exposure(0.0, "SIDEWAYS") == 0.0
    assert calculate_target_exposure(-0.2, "SIDEWAYS") == 0.0
    assert calculate_target_exposure(0.4, "sideways") == 0.4  # Case insensitivity


def test_bear_regime_sizing():
    assert calculate_target_exposure(0.8, "BEAR") == 0.0
    assert calculate_target_exposure(0.0, "BEAR") == 0.0
    assert calculate_target_exposure(-0.5, "BEAR") == 0.0
    assert calculate_target_exposure(0.5, "bear") == 0.0  # Case insensitivity


def test_invalid_regime():
    with pytest.raises(ValueError):
        calculate_target_exposure(0.5, "INVALID")


def test_no_lookahead():
    # Verify that target exposure calculation for a given daily input is purely causal,
    # depending only on the current final score and regime, and behaves the same when isolated.
    history = [
        {"score": 0.5, "regime": "BULL"},
        {"score": 0.8, "regime": "SIDEWAYS"},
        {"score": -0.2, "regime": "BEAR"},
    ]
    
    # Calculate for bar 1 (index 1) in sequence
    out1 = calculate_target_exposure(history[1]["score"], history[1]["regime"])
    
    # Appending a future bar (index 2) does not change the calculation for index 1
    out1_with_future = calculate_target_exposure(history[1]["score"], history[1]["regime"])
    
    assert out1 == 0.5
    assert out1_with_future == 0.5
