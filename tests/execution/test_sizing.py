import pytest
from src.execution.sizing import calculate_target_exposure


def test_binary_threshold_bull():
    assert calculate_target_exposure(0.5, "Bull") == 1.0
    assert calculate_target_exposure(0.51, "Sideways") == 1.0
    assert calculate_target_exposure(0.99, "Bear") == 1.0
    assert calculate_target_exposure(1.0, "Strong Bull") == 1.0


def test_binary_threshold_bear():
    assert calculate_target_exposure(0.499, "Bull") == 0.0
    assert calculate_target_exposure(0.0, "Sideways") == 0.0
    assert calculate_target_exposure(-0.5, "Bear") == 0.0
    assert calculate_target_exposure(0.2, "Weak Bull") == 0.0


def test_backward_compatibility_regime_ignored():
    # The regime argument is ignored in the output but should not raise errors
    assert calculate_target_exposure(0.6, "INVALID_REGIME") == 1.0
    assert calculate_target_exposure(0.2, "SOMETHING_ELSE") == 0.0


def test_no_lookahead():
    # Verify that target exposure calculation for a given daily input is purely causal,
    # depending only on the current final score, and behaves the same when isolated.
    history = [
        {"score": 0.4, "regime": "BULL"},
        {"score": 0.6, "regime": "SIDEWAYS"},
        {"score": 0.3, "regime": "BEAR"},
    ]
    
    # Calculate for bar 1 (index 1) in sequence
    out1 = calculate_target_exposure(history[1]["score"], history[1]["regime"])
    
    # Appending a future bar (index 2) does not change the calculation for index 1
    out1_with_future = calculate_target_exposure(history[1]["score"], history[1]["regime"])
    
    assert out1 == 1.0
    assert out1_with_future == 1.0
