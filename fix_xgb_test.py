with open("tests/ensemble/test_xgboost.py", "r") as f:
    content = f.read()
content = content.replace('np.sign(X_train["Feature1"])', 'np.where(X_train["Feature1"] > 0, 1.0, 0.0)')
with open("tests/ensemble/test_xgboost.py", "w") as f:
    f.write(content)
