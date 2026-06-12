import numpy as np
import pandas as pd


def estimate_ou_halflife_np(x: np.ndarray, min_bars: int = 250, is_returns: bool = True) -> float:
    """
    Estimate the OU half-life from a numpy array of log returns (or log price levels if is_returns=False).
    """
    # Remove NaNs
    x_clean = x[~np.isnan(x)]

    if len(x_clean) < min_bars:
        return 350.0

    # If x represents log returns, convert them to log price levels via cumulative sum
    if is_returns:
        x_levels = np.cumsum(x_clean)
    else:
        x_levels = x_clean

    X = x_levels[:-1]
    Y = x_levels[1:]

    mean_X = np.mean(X)
    mean_Y = np.mean(Y)

    num = np.sum((X - mean_X) * (Y - mean_Y))
    den = np.sum((X - mean_X) ** 2)

    if den <= 0:
        return 350.0

    b = num / den

    if b >= 1.0 or b <= 0.0:
        return 350.0

    hl = -np.log(2.0) / np.log(abs(b))
    return max(120.0, min(350.0, hl))


def estimate_ou_halflife(series: pd.Series, min_bars: int = 250, is_returns: bool = True) -> float:
    """
    Estimate the Ornstein-Uhlenbeck (OU) mean-reversion half-life.

    Discretized AR(1) representation: x_t = a + b * x_{t-1} + e_t
    Half-life is calculated as: HL = -ln(2) / ln(|b|)

    Args:
        series (pd.Series): Daily series (log returns by default).
        min_bars (int): Minimum number of bars required for estimation.
        is_returns (bool): Whether the input series consists of returns (needs cumsum) or levels.

    Returns:
        float: Estimated half-life clamped to [120, 350] days.
    """
    return estimate_ou_halflife_np(series.values, min_bars, is_returns)


def calculate_rolling_ou_halflife(
    series: pd.Series, window: int = 1095, min_bars: int = 250, is_returns: bool = True
) -> pd.Series:
    """
    Calculate the rolling OU half-life over a specified lookback window.

    Args:
        series (pd.Series): Daily series (log returns by default).
        window (int): Size of the rolling window.
        min_bars (int): Minimum number of bars required inside the window.
        is_returns (bool): Whether the input series consists of returns or levels.

    Returns:
        pd.Series: Series of estimated half-lives with same index as input series.
    """
    # Use pandas rolling apply to calculate rolling half-life
    rolling_hl = series.rolling(window=window, min_periods=min_bars).apply(
        lambda x: estimate_ou_halflife_np(x, min_bars, is_returns), raw=True
    )
    return rolling_hl.fillna(350.0)

