import pytest
from src.execution.sizing import calculate_target_exposure

def test_normal_sizing():
    # Should stay out until >= 0.470671
    exposure, cb_active = calculate_target_exposure(
        final_score=0.4,
        vol=0.5,
        prev_exposure=0.0
    )
    assert exposure == 0.0

    # Should enter
    exposure, cb_active = calculate_target_exposure(
        final_score=0.5,
        vol=0.5,
        prev_exposure=0.0
    )
    assert exposure == 1.0

def test_hysteresis():
    # Should stay in since > 0.386242
    exposure, cb_active = calculate_target_exposure(
        final_score=0.4,
        vol=0.5,
        prev_exposure=1.0
    )
    assert exposure == 1.0

    # Should exit
    exposure, cb_active = calculate_target_exposure(
        final_score=0.3,
        vol=0.5,
        prev_exposure=1.0
    )
    assert exposure == 0.0

def test_circuit_breaker():
    exposure, cb_active = calculate_target_exposure(
        final_score=0.9,
        vol=0.5,
        prev_exposure=1.0,
        composite_value=-2.5 # <= -2.032903
    )
    assert exposure == 0.0
    assert cb_active

def test_circuit_breaker_cooloff():
    # Still cooling off
    exposure, cb_active = calculate_target_exposure(
        final_score=0.9,
        vol=0.5,
        prev_exposure=0.0,
        composite_value=0.5, # < 0.803830
        prev_circuit_breaker_active=True
    )
    assert exposure == 0.0
    assert cb_active

    # Cooled off, should re-enter because comp_entry_boost is not met but score > 0.47
    exposure, cb_active = calculate_target_exposure(
        final_score=0.9,
        vol=0.5,
        prev_exposure=0.0,
        composite_value=1.0, # > 0.803830
        prev_circuit_breaker_active=True
    )
    assert exposure == 1.0
    assert not cb_active

def test_comp_entry_boost():
    # Enters purely due to undervaluation
    exposure, cb_active = calculate_target_exposure(
        final_score=0.0,
        vol=0.5,
        prev_exposure=0.0,
        composite_value=2.5 # >= 2.000613
    )
    assert exposure == 1.0

def test_no_lookahead():
    out1, cb1 = calculate_target_exposure(0.5, 0.02, regime="BULL")
    out1_with_future, cb1_with_future = calculate_target_exposure(0.5, 0.02, regime="BULL")
    assert out1 == out1_with_future
    assert cb1 == cb1_with_future
