

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import ElasticNetCV
from sklearn.preprocessing import StandardScaler



class XGBoostEnsemble:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.xgb = xgb.XGBRegressor(
            n_estimators=300,
            learning_rate=0.015,
            max_depth=3,
            subsample=0.6,
            colsample_bytree=0.6,
            objective="reg:squarederror",
            random_state=self.random_state,
            n_jobs=-1
        )
        self.lasso = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.7, 0.9, 0.95, 0.99, 1], 
            alphas=np.logspace(-4, 0, 20),
            cv=3,
            max_iter=5000,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series):
        if X.empty or len(y) == 0:
            raise ValueError("Training data cannot be empty.")

        y = pd.Series(y, index=X.index)
        
        self.xgb.fit(X, y)
        X_scaled = self.scaler.fit_transform(X)
        self.lasso.fit(X_scaled, y)
        self.fitted = True

    def predict(self, X: pd.DataFrame) -> pd.Series:
        if not self.fitted:
            raise ValueError("Model must be fitted before calling predict_score.")

        if X.empty:
            return pd.Series(dtype=float)

        preds_xgb = self.xgb.predict(X)
        X_scaled = self.scaler.transform(X)
        preds_lasso = self.lasso.predict(X_scaled)
        
        # Ensemble average: 80% XGBoost, 20% Lasso
        preds = (preds_xgb * 0.3) + (preds_lasso * 0.7)
        preds = np.clip(preds, 0.0, 1.0)
        return pd.Series(preds, index=X.index)


