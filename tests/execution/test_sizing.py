import pytest
from src.execution.sizing import (
    calculate_target_exposure,
    SCORE_ENTRY,
    SCORE_EXIT,
    CB_ACTIVATE,
    CB_COOLOFF,
    COMP_ENTRY_BOOST,
)

def test_normal_sizing():
    # Should stay out until >= SCORE_ENTRY
    exposure, cb_active = calculate_target_exposure(
        smoothed_score_entry=SCORE_ENTRY - 0.01,
        smoothed_score_exit=0.0,
        vol=0.5,
        prev_exposure=0.0
    )
    assert exposure == 0.0

    # Should enter
    exposure, cb_active = calculate_target_exposure(
        smoothed_score_entry=SCORE_ENTRY + 0.01,
        smoothed_score_exit=0.0,
        vol=0.5,
        prev_exposure=0.0
    )
    assert exposure == 1.0

def test_hysteresis():
    # Should stay in since > SCORE_EXIT
    exposure, cb_active = calculate_target_exposure(
        smoothed_score_entry=0.0,
        smoothed_score_exit=SCORE_EXIT + 0.01,
        vol=0.5,
        prev_exposure=1.0
    )
    assert exposure == 1.0

    # Should exit
    exposure, cb_active = calculate_target_exposure(
        smoothed_score_entry=0.0,
        smoothed_score_exit=SCORE_EXIT - 0.01,
        vol=0.5,
        prev_exposure=1.0
    )
    assert exposure == 0.0

def test_circuit_breaker():
    exposure, cb_active = calculate_target_exposure(
        smoothed_score_entry=0.9,
        smoothed_score_exit=0.9,
        vol=0.5,
        prev_exposure=1.0,
        composite_value=CB_ACTIVATE - 0.1
    )
    assert exposure == 0.0
    assert cb_active

def test_circuit_breaker_cooloff():
    # Still cooling off
    exposure, cb_active = calculate_target_exposure(
        smoothed_score_entry=0.9,
        smoothed_score_exit=0.9,
        vol=0.5,
        prev_exposure=0.0,
        composite_value=CB_COOLOFF - 0.1,
        prev_circuit_breaker_active=True
    )
    assert exposure == 0.0
    assert cb_active

    # Cooled off, should re-enter because comp_entry_boost is not met but score > SCORE_ENTRY
    exposure, cb_active = calculate_target_exposure(
        smoothed_score_entry=SCORE_ENTRY + 0.01,
        smoothed_score_exit=SCORE_ENTRY + 0.01,
        vol=0.5,
        prev_exposure=0.0,
        composite_value=CB_COOLOFF + 0.1,
        prev_circuit_breaker_active=True
    )
    assert exposure == 1.0
    assert not cb_active

def test_comp_entry_boost():
    # Enters purely due to undervaluation
    exposure, cb_active = calculate_target_exposure(
        smoothed_score_entry=0.0,
        smoothed_score_exit=0.0,
        vol=0.5,
        prev_exposure=0.0,
        composite_value=COMP_ENTRY_BOOST + 0.1
    )
    assert exposure == 1.0

def test_no_lookahead():
    out1, cb1 = calculate_target_exposure(0.5, 0.5, 0.02, regime="BULL")
    out1_with_future, cb1_with_future = calculate_target_exposure(0.5, 0.5, 0.02, regime="BULL")
    assert out1 == out1_with_future
    assert cb1 == cb1_with_future
