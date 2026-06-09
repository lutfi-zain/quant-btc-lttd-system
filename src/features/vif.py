import pandas as pd


def calculate_vif(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Variance Inflation Factor (VIF) for each column in a DataFrame.
    """
    from sklearn.linear_model import LinearRegression

    vifs = pd.Series(index=df.columns, dtype=float)
    for col in df.columns:
        if df[col].var() == 0:
            vifs[col] = float("inf")
            continue
        other_cols = [c for c in df.columns if c != col]
        if not other_cols:
            vifs[col] = 1.0
            continue
        X = df[other_cols]
        y = df[col]
        reg = LinearRegression().fit(X, y)
        r_sq = reg.score(X, y)
        if r_sq >= 1.0:
            vifs[col] = float("inf")
        else:
            vifs[col] = 1.0 / (1.0 - r_sq)
    return vifs


def pratt_measure(X: pd.DataFrame, y: pd.Series) -> pd.Series:
    """
    Calculate Pratt's Measure for features in X relative to target y.
    d_j = beta_j * r_j / R^2
    """
    from sklearn.linear_model import LinearRegression

    # Ensure y is a pandas Series with same index as X
    y = pd.Series(y, index=X.index)

    # Standardize X and y to get beta coefficients
    X_mean = X.mean()
    X_std = X.std()
    y_mean = y.mean()
    y_std = y.std()

    # Avoid division by zero
    X_std_val = X_std.replace(0.0, 1.0)
    y_std_val = 1.0 if y_std == 0.0 else y_std

    X_std_df = (X - X_mean) / X_std_val
    y_std_ser = (y - y_mean) / y_std_val

    reg = LinearRegression().fit(X_std_df, y_std_ser)
    R_sq = reg.score(X_std_df, y_std_ser)

    if R_sq <= 0:
        return pd.Series(0.0, index=X.columns)

    betas = reg.coef_
    r_js = X_std_df.corrwith(y_std_ser)

    pratt = {}
    for i, col in enumerate(X.columns):
        beta_j = betas[i]
        r_j = r_js[col]
        if pd.isna(beta_j) or pd.isna(r_j):
            pratt[col] = 0.0
        else:
            pratt[col] = (beta_j * r_j) / R_sq

    return pd.Series(pratt)


def prune_multicollinear_indicators(
    df: pd.DataFrame, y: pd.Series, vif_threshold: float = 10.0
) -> pd.DataFrame:
    """
    Step-wise pruning of indicators using VIF and Pratt's Measure.
    """
    current_df = df.copy()
    y = pd.Series(y, index=df.index)

    while True:
        if current_df.shape[1] <= 1:
            break

        vifs = calculate_vif(current_df)
        high_vif_cols = vifs[vifs > vif_threshold].index.tolist()

        if not high_vif_cols:
            break

        # Compute Pratt's Measure for current columns
        pratt = pratt_measure(current_df, y)

        # Find the column among high_vif_cols with the lowest Pratt measure
        col_to_drop = min(high_vif_cols, key=lambda c: pratt[c])
        current_df = current_df.drop(columns=[col_to_drop])

    return current_df
