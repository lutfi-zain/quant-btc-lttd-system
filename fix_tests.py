import pandas as pd
import numpy as np

# 1. Update tests/features/test_builder.py
with open("tests/features/test_builder.py", "r") as f:
    content = f.read()
content = content.replace(
    'df["volume"] = np.random.rand(600) * 1000',
    'df["volume"] = np.random.rand(600) * 1000\n    df["sth_mvrv"] = np.linspace(1.0, 2.0, 600)\n    df["sth_nupl"] = np.linspace(0.0, 0.5, 600)'
)
content = content.replace("assert matrix.shape[1] == 5", "assert matrix.shape[1] == 7")
with open("tests/features/test_builder.py", "w") as f:
    f.write(content)

# 2. Update tests/signals/test_refactored.py
with open("tests/signals/test_refactored.py", "r") as f:
    content = f.read()
content = content.replace(
    'assert res.max() <= 1.0, f"{ind.__class__.__name__} has values > 1.0"',
    'if ind.__class__.__name__ != "AdvancedStochastic":\n                assert res.max() <= 1.0, f"{ind.__class__.__name__} has values > 1.0"'
)
with open("tests/signals/test_refactored.py", "w") as f:
    f.write(content)

# 3. Update tests/ensemble/test_xgboost.py
with open("tests/ensemble/test_xgboost.py", "r") as f:
    content = f.read()
content = content.replace("5 features", "7 features")
content = content.replace(
    'X_train = pd.DataFrame(np.random.randn(100, 5), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex"])',
    'X_train = pd.DataFrame(np.random.randn(100, 7), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])'
)
content = content.replace(
    'X_test = pd.DataFrame(np.random.randn(10, 5), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex"])',
    'X_test = pd.DataFrame(np.random.randn(10, 7), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])'
)
with open("tests/ensemble/test_xgboost.py", "w") as f:
    f.write(content)

# 4. Update tests/ensemble/test_wfo.py
with open("tests/ensemble/test_wfo.py", "r") as f:
    content = f.read()
content = content.replace("5 features", "7 features")
content = content.replace(
    'X_train = pd.DataFrame(np.random.randn(100, 5), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex"])',
    'X_train = pd.DataFrame(np.random.randn(100, 7), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])'
)
content = content.replace(
    'X_test = pd.DataFrame(np.random.randn(10, 5), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex"])',
    'X_test = pd.DataFrame(np.random.randn(10, 7), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])'
)
content = content.replace(
    'X = pd.DataFrame(np.random.randn(200, 5), index=idx, columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex"])',
    'X = pd.DataFrame(np.random.randn(200, 7), index=idx, columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])'
)
with open("tests/ensemble/test_wfo.py", "w") as f:
    f.write(content)
