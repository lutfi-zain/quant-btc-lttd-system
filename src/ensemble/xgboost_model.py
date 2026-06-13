
import numpy as np
import pandas as pd
import xgboost as xgb



class XGBoostEnsemble:
    """
    Layer 4: Ensemble Aggregation using XGBoost.
    Predicts probability of an uptrend.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.xgb = xgb.XGBRegressor(
            n_estimators=500,
            learning_rate=0.01,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            objective="reg:squarederror",
            random_state=self.random_state,
            n_jobs=-1
        )

        self.fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series):
        if X.empty or len(y) == 0:
            raise ValueError("Training data cannot be empty.")

        y = pd.Series(y, index=X.index)
        
        self.xgb.fit(X, y)
        
        self.fitted = True

    def predict_score(self, X: pd.DataFrame) -> pd.Series:
        if not self.fitted:
            raise ValueError("Model must be fitted before calling predict_score.")

        if X.empty:
            return pd.Series(dtype=float)

        preds_xgb = self.xgb.predict(X)
        
        
        # Ensemble average
        preds = preds_xgb
        preds = np.clip(preds, 0.0, 1.0)
        return pd.Series(preds, index=X.index)



    def predict(self, X: pd.DataFrame) -> pd.Series:
        return self.predict_score(X)

    def get_feature_importances(self, X: pd.DataFrame) -> pd.Series:
        if not self.fitted:
            raise ValueError("Model must be fitted")
        return pd.Series(self.model.feature_importances_, index=X.columns)

