from src.regime.filter import apply_onchain_overrides


def test_sth_nupl_override():
    # Normal case: no override
    posteriors = {"BULL": 0.80, "BEAR": 0.10, "SIDEWAYS": 0.10}
    metrics = {"sth_nupl": 0.50}
    res = apply_onchain_overrides(posteriors, metrics)
    assert res["BULL"] == 0.80

    # Override case: sth_nupl > 0.75
    metrics = {"sth_nupl": 0.80}
    res = apply_onchain_overrides(posteriors, metrics)
    assert res["BULL"] == 0.50
    # Remaining 0.30 distributed proportionally to BEAR (0.1) and SIDEWAYS (0.1)
    # Since they are equal, they should both get 0.15 more, making them 0.25 each.
    assert res["BEAR"] == 0.25
    assert res["SIDEWAYS"] == 0.25
    assert sum(res.values()) == pytest_sum_check(res)


def test_sth_mvrv_override():
    # Normal case: no override
    posteriors = {"BULL": 0.80, "BEAR": 0.10, "SIDEWAYS": 0.10}
    metrics = {"sth_mvrv": 1.50}
    res = apply_onchain_overrides(posteriors, metrics)
    assert res["BULL"] == 0.80

    # Override case: sth_mvrv > 2.0
    metrics = {"sth_mvrv": 2.20}
    res = apply_onchain_overrides(posteriors, metrics)
    assert res["BULL"] == 0.0
    # Remaining 0.80 distributed proportionally to BEAR (0.1) and SIDEWAYS (0.1)
    # They should both get 0.40 more, making them 0.50 each.
    assert res["BEAR"] == 0.50
    assert res["SIDEWAYS"] == 0.50
    assert sum(res.values()) == pytest_sum_check(res)


def pytest_sum_check(res):
    return round(sum(res.values()), 5)
