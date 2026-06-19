import os

# 1. Fix utils.py missing np
with open("tests/signals/utils.py", "r") as f:
    content = f.read()
if "import numpy as np" not in content:
    content = "import numpy as np\n" + content
with open("tests/signals/utils.py", "w") as f:
    f.write(content)

# 2. Fix test_builder.py
with open("tests/features/test_builder.py", "r") as f:
    content = f.read()
content = content.replace("assert matrix.shape[1] == 7", "assert matrix.shape[1] == 11")
with open("tests/features/test_builder.py", "w") as f:
    f.write(content)

# 3. Fix test_xgboost.py and test_wfo.py
with open("tests/ensemble/test_xgboost.py", "r") as f:
    content = f.read()
content = content.replace("7 features", "11 features")
content = content.replace(
    'X_train = pd.DataFrame(np.random.randn(100, 7), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])',
    'X_train = pd.DataFrame(np.random.randn(100, 11), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "TrendStrengthIndex", "DivergenceSignal", "JMA_30", "sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit", "sth_mvrv_roc_7"])'
)
content = content.replace(
    'X_test = pd.DataFrame(np.random.randn(10, 7), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])',
    'X_test = pd.DataFrame(np.random.randn(10, 11), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "TrendStrengthIndex", "DivergenceSignal", "JMA_30", "sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit", "sth_mvrv_roc_7"])'
)
with open("tests/ensemble/test_xgboost.py", "w") as f:
    f.write(content)

with open("tests/ensemble/test_wfo.py", "r") as f:
    content = f.read()
content = content.replace("7 features", "11 features")
content = content.replace(
    'X_train = pd.DataFrame(np.random.randn(100, 7), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])',
    'X_train = pd.DataFrame(np.random.randn(100, 11), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "TrendStrengthIndex", "DivergenceSignal", "JMA_30", "sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit", "sth_mvrv_roc_7"])'
)
content = content.replace(
    'X_test = pd.DataFrame(np.random.randn(10, 7), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])',
    'X_test = pd.DataFrame(np.random.randn(10, 11), columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "TrendStrengthIndex", "DivergenceSignal", "JMA_30", "sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit", "sth_mvrv_roc_7"])'
)
content = content.replace(
    'X = pd.DataFrame(np.random.randn(200, 7), index=idx, columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "QuantileDEMA", "TrendStrengthIndex", "DivergenceSignal", "JMA_30"])',
    'X = pd.DataFrame(np.random.randn(200, 11), index=idx, columns=["AdvancedStochastic", "RSI-50", "FourierSupertrend", "TrendStrengthIndex", "DivergenceSignal", "JMA_30", "sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit", "sth_mvrv_roc_7"])'
)
with open("tests/ensemble/test_wfo.py", "w") as f:
    f.write(content)
