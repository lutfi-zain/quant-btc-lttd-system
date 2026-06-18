import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import StandardScaler

class XGBoostEnsemble:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.xgb = None
        self.scaler = StandardScaler()
        self.fitted = False
        self.single_class = False

    def fit(self, X: pd.DataFrame, y: pd.Series):
        if X.empty or len(y) == 0:
            raise ValueError("Training data cannot be empty.")

        valid_idx = y.notna()
        X = X[valid_idx]
        y = y[valid_idx]
        
        if X.empty:
            raise ValueError("Training data cannot be empty after NaN drop.")

        num_pos = (y >= 0.5).sum()
        num_neg = (y < 0.5).sum()

        scale_pos_weight = num_neg / max(1, num_pos)
        
        # reg:squarederror for continuous target in [-1, +1]
        self.xgb = xgb.XGBRegressor(
            n_estimators=200,         
            learning_rate=0.05,
            max_depth=5,              
            subsample=0.8,            
            colsample_bytree=0.8,     
            objective="reg:squarederror",
            random_state=self.random_state,
            n_jobs=1,
            reg_alpha=0.1,            
            reg_lambda=0.1            
        )
        
        X_scaled = self.scaler.fit_transform(X)
        self.xgb.fit(X_scaled, y)
        self.fitted = True

    def predict(self, X: pd.DataFrame) -> pd.Series:
        if not self.fitted:
            raise ValueError("Model must be fitted before calling predict.")

        if X.empty:
            return pd.Series(dtype=float)

        X_scaled = self.scaler.transform(X)
        preds_prob = self.xgb.predict(X_scaled)
        
        return pd.Series(preds_prob, index=X.index)
