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
    if len(close) < 200:
        raise ValueError(
            f"Insufficient data for stable Regime classification. Provided {len(close)} days, "
            f"minimum 200 days required."
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

    means = np.zeros((3, 3))
    covars = np.zeros((3, 3))
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

    # Deterministic State Labeling based on Macro Trend (sma_dist is feature index 2):
    # - Highest sma_dist -> BULL (Price far above 200 SMA)
    # - Lowest sma_dist -> BEAR (Price far below 200 SMA)
    # - Intermediate sma_dist -> SIDEWAYS
    means_ = model.means_

    bull_idx = int(np.argmax(means_[:, 2]))
    remaining = [i for i in [0, 1, 2] if i != bull_idx]

    if means_[remaining[0], 2] < means_[remaining[1], 2]:
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
    ema_span: int = 1,
) -> Dict[str, Any]:
    """
    Infer the market regime for the latest day in the provided close prices.

    Args:
        model (hmm.GaussianHMM): The trained HMM model.
        state_to_regime (Dict[int, str]): Mapping from HMM state index to regime name.
        close (pd.Series): Historical close prices.
        window (int): Rolling volatility window. Default is 21.
        ema_span (int): Exponential moving average span for posterior smoothing. Default is 1 (no smoothing).

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

    # Run predict_proba for all samples
    proba = model.predict_proba(features)
    
    if ema_span > 1:
        # Smooth posteriors causally using EMA
        df_proba = pd.DataFrame(proba)
        df_proba_smoothed = df_proba.ewm(span=ema_span, adjust=False).mean()
        latest_proba = df_proba_smoothed.iloc[-1].values
    else:
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
    ema_span: int = 1,
) -> pd.DataFrame:
    """
    Infer the market regime historically for all days in the prepared features.

    Args:
        model (hmm.GaussianHMM): The trained HMM model.
        state_to_regime (Dict[int, str]): Mapping from HMM state index to regime name.
        close (pd.Series): Historical close prices.
        window (int): Rolling volatility window. Default is 21.
        ema_span (int): Exponential moving average span for posterior smoothing. Default is 1 (no smoothing).

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

    df_proba = pd.DataFrame(
        {
            "p_bull": p_bull,
            "p_bear": p_bear,
            "p_sideways": p_sideways,
        },
        index=features_df.index,
    )

    if ema_span > 1:
        df_proba = df_proba.ewm(span=ema_span, adjust=False).mean()

    # Classification logic: choose the state with the highest probability (argmax)
    regimes = df_proba.idxmax(axis=1).map(
        {
            "p_bull": "BULL",
            "p_bear": "BEAR",
            "p_sideways": "SIDEWAYS"
        }
    ).tolist()

    res = pd.DataFrame(
        {
            "p_bull": df_proba["p_bull"],
            "p_bear": df_proba["p_bear"],
            "p_sideways": df_proba["p_sideways"],
            "regime": regimes,
        },
        index=features_df.index,
    )

    return res

