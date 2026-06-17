import numpy as np
import pandas as pd


def calculate_log_returns(close: pd.Series) -> pd.Series:
    """
    Calculate daily log returns ln(P_t / P_{t-1}) causally.

    Args:
        close (pd.Series): Historical daily close prices.

    Returns:
        pd.Series: Daily log returns.
    """
    return np.log(close / close.shift(1))


def calculate_realized_volatility(
    log_returns: pd.Series, window: int = 21
) -> pd.Series:
    """
    Calculate realized volatility using a rolling window of log returns causally.

    Args:
        log_returns (pd.Series): Daily log returns.
        window (int): Rolling window size. Default is 21.

    Returns:
        pd.Series: Rolling realized volatility.
    """
    return log_returns.rolling(window=window).std()


def prepare_features_df(close: pd.Series, window: int = 21) -> pd.DataFrame:
    """
    Orchestrate log returns, volatility, and SMA distance into a aligned DataFrame, dropping NaNs.

    Args:
        close (pd.Series): Historical daily close prices.
        window (int): Volatility rolling window size. Default is 21.

    Returns:
        pd.DataFrame: Aligned features DataFrame with columns 'log_returns', 'realized_volatility', 'sma_dist'.
    """
    log_returns = calculate_log_returns(close)
    vol = calculate_realized_volatility(log_returns, window=window)
    
    # Macro trend feature to prevent HMM lag and noise
    sma200 = close.rolling(window=200).mean()
    sma_dist = (close - sma200) / sma200
    
    df = pd.DataFrame({
        "log_returns": log_returns, 
        "realized_volatility": vol,
        "sma_dist": sma_dist
    })
    df.dropna(inplace=True)
    return df


def prepare_features(close: pd.Series, window: int = 21) -> np.ndarray:
    """
    Orchestrate log returns and volatility into the exact 2D array expected by HMM.

    Args:
        close (pd.Series): Historical daily close prices.
        window (int): Volatility rolling window size. Default is 21.

    Returns:
        np.ndarray: 2D array of features of shape (n_samples, 2).
    """
    df = prepare_features_df(close, window)
    return df.values
