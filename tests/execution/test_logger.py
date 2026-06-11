import pytest
from src.execution.logger import RegimeTransitionLogger


def test_no_transition_no_log():
    # Initialize logger with BULL
    transition_logger = RegimeTransitionLogger(previous_regime="BULL")

    # Feed BULL again, check_and_log should return None (no transition)
    payload = transition_logger.check_and_log(
        current_regime="BULL",
        brk_stamp="2026-06-08",
        p_bull=0.9,
        p_bear=0.05,
        p_sideways=0.05,
        log_return=0.02,
        realized_volatility=0.15,
    )
    assert payload is None
    assert transition_logger.previous_regime == "BULL"


def test_transition_logs_exact_keys():
    # Initialize logger with BULL
    transition_logger = RegimeTransitionLogger(previous_regime="BULL")

    # Shift to BEAR, check_and_log should detect the transition and return payload
    payload = transition_logger.check_and_log(
        current_regime="BEAR",
        brk_stamp="2026-06-09",
        p_bull=0.05,
        p_bear=0.9,
        p_sideways=0.05,
        log_return=-0.04,
        realized_volatility=0.25,
    )
    assert payload is not None
    assert transition_logger.previous_regime == "BEAR"

    # Verify all required keys are present with exact names
    expected_keys = {
        "Regime",
        "BRK Stamp",
        "P(Bull)",
        "P(Bear)",
        "P(Sideways)",
        "Log Return",
        "Realized Volatility",
    }
    assert set(payload.keys()) == expected_keys

    # Verify correctness of values
    assert payload["Regime"] == "BEAR"
    assert payload["BRK Stamp"] == "2026-06-09"
    assert payload["P(Bull)"] == 0.05
    assert payload["P(Bear)"] == 0.9
    assert payload["P(Sideways)"] == 0.05
    assert payload["Log Return"] == -0.04
    assert payload["Realized Volatility"] == 0.25


def test_none_previous_initialization():
    transition_logger = RegimeTransitionLogger(previous_regime=None)

    # First call sets the regime but shouldn't log
    payload1 = transition_logger.check_and_log(
        current_regime="BULL",
        brk_stamp="2026-06-08",
        p_bull=0.9,
        p_bear=0.05,
        p_sideways=0.05,
        log_return=0.02,
        realized_volatility=0.15,
    )
    assert payload1 is None
    assert transition_logger.previous_regime == "BULL"

    # Second call changes regime, should log
    payload2 = transition_logger.check_and_log(
        current_regime="SIDEWAYS",
        brk_stamp="2026-06-09",
        p_bull=0.2,
        p_bear=0.1,
        p_sideways=0.7,
        log_return=-0.01,
        realized_volatility=0.18,
    )
    assert payload2 is not None
    assert payload2["Regime"] == "SIDEWAYS"
