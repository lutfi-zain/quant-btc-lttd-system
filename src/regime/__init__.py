"""
Regime Detection Layer (Layer 1).

Exposes public training and inference interfaces for Hidden Markov Model (HMM) regime detection.
"""

from src.regime.hmm import train_hmm, infer_regime, infer_regime_history

__all__ = [
    "train_hmm",
    "infer_regime",
    "infer_regime_history",
]
