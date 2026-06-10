import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def calculate_pratt_importance(X: pd.DataFrame, y: pd.Series) -> pd.Series:
    """
    Calculate Pratt's Relative Importance Measure for features in X relative to target y.
    Formula: d_j = beta_j * r_j / R^2
    Where beta_j is the standardized coefficient and r_j is the correlation.
    """
    if X.empty or len(y) == 0:
        return pd.Series(0.0, index=X.columns)

    # Ensure y has the same index as X
    y = pd.Series(y, index=X.index)

    # Standardize X and y (Z-score normalization)
    X_mean = X.mean()
    X_std = X.std()
    y_mean = y.mean()
    y_std = y.std()

    # Avoid division by zero
    X_std_val = X_std.replace(0.0, 1.0)
    y_std_val = 1.0 if y_std == 0.0 else y_std

    X_scaled = (X - X_mean) / X_std_val
    y_scaled = (y - y_mean) / y_std_val

    # Fit linear regression on standardized variables
    reg = LinearRegression().fit(X_scaled, y_scaled)
    R_sq = reg.score(X_scaled, y_scaled)

    # If R^2 is <= 0 (no predictive power), return zero importance
    if R_sq <= 0.0:
        return pd.Series(0.0, index=X.columns)

    betas = reg.coef_
    r_js = X_scaled.corrwith(y_scaled)

    pratt = {}
    for i, col in enumerate(X.columns):
        beta_j = betas[i]
        r_j = r_js[col]
        if pd.isna(beta_j) or pd.isna(r_j):
            pratt[col] = 0.0
        else:
            # Pratt's measure
            pratt[col] = (beta_j * r_j) / R_sq

    return pd.Series(pratt)


def rank_and_flag_features(pratt_scores: pd.Series) -> pd.DataFrame:
    """
    Ranks features based on their Pratt's Measure, and flags features
    with less than 1% contribution (< 0.01) for potential removal.
    """
    # Sort descending
    sorted_scores = pratt_scores.sort_values(ascending=False)
    
    ranks = np.arange(1, len(sorted_scores) + 1)
    
    df_report = pd.DataFrame({
        "pratt_measure": sorted_scores,
        "rank": ranks,
        "flagged_for_removal": sorted_scores < 0.01
    }, index=sorted_scores.index)
    
    return df_report
