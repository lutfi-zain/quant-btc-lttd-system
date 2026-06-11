import logging
import json
from typing import Optional, Dict, Any

# Configure logger
logger = logging.getLogger("RegimeTransitionLogger")


class RegimeTransitionLogger:
    """
    Tracks HMM regime transitions and logs them using a standardized structured format.
    """

    def __init__(self, previous_regime: Optional[str] = None):
        self.previous_regime = previous_regime.upper() if previous_regime else None

    def check_and_log(
        self,
        current_regime: str,
        brk_stamp: str,
        p_bull: float,
        p_bear: float,
        p_sideways: float,
        log_return: float,
        realized_volatility: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Detects if current_regime differs from previous_regime.
        If a shift occurs, logs a structured message with exact terms.
        """
        current_regime_upper = current_regime.upper()

        # Check if a transition has occurred (only when previous_regime was set to a different value)
        transition_occurred = (
            self.previous_regime is not None
            and self.previous_regime != current_regime_upper
        )

        log_payload = None
        if transition_occurred:
            log_payload = {
                "Regime": current_regime_upper,
                "BRK Stamp": brk_stamp,
                "P(Bull)": p_bull,
                "P(Bear)": p_bear,
                "P(Sideways)": p_sideways,
                "Log Return": log_return,
                "Realized Volatility": realized_volatility,
            }
            # Print/log to stdout/logger using the exact terms
            logger.info(f"[REGIME_TRANSITION] {json.dumps(log_payload)}")

        # Always update the tracking state
        self.previous_regime = current_regime_upper
        return log_payload
