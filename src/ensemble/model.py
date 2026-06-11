import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from src.features.importance import calculate_pratt_importance


class L1LassoEnsemble:
    """
    Layer 4: Ensemble Aggregation.
    Fits an L1-Lasso Logistic Regression model on PCA-orthogonalized features
    to output a Final Score ∈ [-1.0, +1.0].
    Also computes Pratt's Measure for indicator importance diagnostics.
    """

    def __init__(self, C: float = 1.0, random_state: int = 42):
        self.C = C
        self.random_state = random_state
        self.model = LogisticRegression(
            solver="liblinear",  # Stable and efficient for L1 optimization
            l1_ratio=1.0,        # Specifies L1 penalty in sklearn 1.8+
            C=self.C,
            random_state=self.random_state,
        )
        self.fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series):
        if X.empty or len(y) == 0:
            raise ValueError("Training data cannot be empty.")

        # Align target index
        y = pd.Series(y, index=X.index)

        # Fit model
        self.model.fit(X, y)
        self.fitted = True

    def predict_score(self, X: pd.DataFrame) -> pd.Series:
        """
        Predicts a continuous probabilistic Final Score ∈ [-1.0, +1.0].
        Formula: Final Score = 2 * P(y=1) - 1
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before calling predict_score.")

        if X.empty:
            return pd.Series(dtype=float)

        # Predict probability for class 1 (up trend)
        probs = self.model.predict_proba(X)[:, 1]

        # Scale from [0, 1] to [-1.0, +1.0]
        final_scores = 2.0 * probs - 1.0

        return pd.Series(final_scores, index=X.index)

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """
        Expose stateless-compatible predict interface returning the continuous Final Score ∈ [-1.0, +1.0].
        """
        return self.predict_score(X)

    def calculate_pratt(self, X: pd.DataFrame, y: pd.Series) -> pd.Series:
        """
        Calculates Pratt's Measure (d_j = beta_j * r_j / R^2) for features in X.
        Uses the helper from src.features.importance.
        """
        return calculate_pratt_importance(X, y)
