import re

with open("tests/features/test_builder.py", "r") as f:
    content = f.read()

# Fix the shape test
content = content.replace(
'''        assert sorted(list(matrix.columns)) == sorted(
            [
                "AdvancedStochastic",
                "RSI-50",
                "FourierSupertrend",
                "TrendStrengthIndex",
            ]
        )''',
'''        assert sorted(list(matrix.columns)) == sorted(
            [
                "AdvancedStochastic",
                "RSI-50",
                "FourierSupertrend",
                "TrendStrengthIndex",
                "DivergenceSignal",
                "JMA_30",
            ]
        )''')

# Fix the VIF test to avoid infinity due to all-zeros DivergenceSignal
# Let's add a dummy sth_mvrv to the sample_data fixture, wait, sample_data is a fixture in conftest?
# Actually we can just drop constant columns before VIF calculation in the test,
# or we can mock DivergenceSignal.
