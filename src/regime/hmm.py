from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
from hmmlearn import hmm
from sklearn.cluster import KMeans
from src.regime.features import prepare_features, prepare_features_df


def train_hmm(
    close: pd.Series, window: int = 21
) -> Tuple[hmm.GaussianHMM, Dict[int, str]]:
    """
    Train a 3-state Gaussian HMM on features prepared from close prices.

    Args:
        close (pd.Series): Historical daily close prices (minimum 120 days).
        window (int): Rolling volatility window. Default is 21.

    Returns:
        Tuple[hmm.GaussianHMM, Dict[int, str]]: Fitted model and state-to-regime mapping.
    """
    if len(close) < 120:
        raise ValueError(
            f"Insufficient data for stable Regime classification. Provided {len(close)} days, "
            f"minimum 120 days required."
        )

    # Prepare features
    features = prepare_features(close, window=window)

    # 3-state HMM
    model = hmm.GaussianHMM(
        n_components=3, covariance_type="diag", n_iter=100, random_state=42
    )

    # Robust K-Means initialization
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(features)

    means = np.zeros((3, 2))
    covars = np.zeros((3, 2))
    for i in range(3):
        cluster_data = features[labels == i]
        if len(cluster_data) > 0:
            means[i] = cluster_data.mean(axis=0)
            covars[i] = cluster_data.var(axis=0)
        else:
            # Fallback if a cluster is empty (highly unlikely with KMeans)
            means[i] = features.mean(axis=0)
            covars[i] = features.var(axis=0)

    # Avoid singular covariances by adding a small floor/epsilon
    covars = np.clip(covars, a_min=1e-6, a_max=None)

    model.means_ = means
    model.covars_ = covars
    model.init_params = "st"  # Initialize startprob_ and transmat_ automatically

    # Fit the HMM model
    model.fit(features)

    # Deterministic State Labeling:
    # - Highest mean return -> BULL
    # - Lowest mean return -> BEAR
    # - Intermediate mean return -> SIDEWAYS
    means_ = model.means_

    bull_idx = int(np.argmax(means_[:, 0]))
    remaining = [i for i in [0, 1, 2] if i != bull_idx]

    if means_[remaining[0], 0] < means_[remaining[1], 0]:
        bear_idx = remaining[0]
        sideways_idx = remaining[1]
    else:
        bear_idx = remaining[1]
        sideways_idx = remaining[0]

    state_to_regime = {bull_idx: "BULL", bear_idx: "BEAR", sideways_idx: "SIDEWAYS"}

    return model, state_to_regime


def infer_regime(
    model: hmm.GaussianHMM,
    state_to_regime: Dict[int, str],
    close: pd.Series,
    window: int = 21,
) -> Dict[str, Any]:
    """
    Infer the market regime for the latest day in the provided close prices.

    Args:
        model (hmm.GaussianHMM): The trained HMM model.
        state_to_regime (Dict[int, str]): Mapping from HMM state index to regime name.
        close (pd.Series): Historical close prices.
        window (int): Rolling volatility window. Default is 21.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'regime': The classified regime (BULL, BEAR, or SIDEWAYS).
            - 'posteriors': Dict mapping regime name to posterior probability.
    """
    # Prepare features
    features = prepare_features(close, window=window)
    if len(features) == 0:
        raise ValueError("Insufficient features generated to run inference.")

    # Bound features to training window size (1095 days) to prevent historical drift
    if len(features) > 1095:
        features = features[-1095:]

    # Run predict_proba for all samples, and take the last sample (current day)
    proba = model.predict_proba(features)
    latest_proba = proba[-1]

    # Map probabilities to regime names
    posteriors = {state_to_regime[i]: float(latest_proba[i]) for i in range(3)}

    # Classification logic: choose the state with the highest probability (argmax)
    regime = max(posteriors, key=posteriors.get)

    return {"regime": regime, "posteriors": posteriors}


def infer_regime_history(
    model: hmm.GaussianHMM,
    state_to_regime: Dict[int, str],
    close: pd.Series,
    window: int = 21,
) -> pd.DataFrame:
    """
    Infer the market regime historically for all days in the prepared features.

    Args:
        model (hmm.GaussianHMM): The trained HMM model.
        state_to_regime (Dict[int, str]): Mapping from HMM state index to regime name.
        close (pd.Series): Historical close prices.
        window (int): Rolling volatility window. Default is 21.

    Returns:
        pd.DataFrame: DataFrame indexed by date with columns:
            - 'p_bull', 'p_bear', 'p_sideways'
            - 'regime'
    """
    features_df = prepare_features_df(close, window=window)
    if len(features_df) == 0:
        return pd.DataFrame()

    features = features_df.values
    proba = np.zeros((len(features_df), 3))
    for i in range(len(features_df)):
        start_idx = max(0, i - 1095 + 1)
        sub_features = features[start_idx : i + 1]
        p = model.predict_proba(sub_features)
        proba[i] = p[-1]

    bull_col = [k for k, v in state_to_regime.items() if v == "BULL"][0]
    bear_col = [k for k, v in state_to_regime.items() if v == "BEAR"][0]
    side_col = [k for k, v in state_to_regime.items() if v == "SIDEWAYS"][0]

    p_bull = proba[:, bull_col]
    p_bear = proba[:, bear_col]
    p_sideways = proba[:, side_col]

    regimes = []
    for idx in range(len(proba)):
        pb = p_bull[idx]
        pr = p_bear[idx]
        ps = p_sideways[idx]
        state_probs = {"BULL": pb, "BEAR": pr, "SIDEWAYS": ps}
        regimes.append(max(state_probs, key=state_probs.get))

    res = pd.DataFrame(
        {
            "p_bull": p_bull,
            "p_bear": p_bear,
            "p_sideways": p_sideways,
            "regime": regimes,
        },
        index=features_df.index,
    )

    return res

