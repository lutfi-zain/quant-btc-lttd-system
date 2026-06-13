from typing import Dict, Optional
from src.execution.database import get_connection, DEFAULT_DB_PATH


def upsert_daily_lttd(
    date: str,
    regime: str,
    final_score: float,
    db_path=DEFAULT_DB_PATH,
    target_exposure: float = 0.0,
    posterior_prob: Optional[float] = None,
):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO daily_lttd (data_as_of, date, regime, final_score, target_exposure, posterior_prob)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(data_as_of) DO UPDATE SET
                date = excluded.date,
                regime = excluded.regime,
                final_score = excluded.final_score,
                target_exposure = excluded.target_exposure,
                posterior_prob = excluded.posterior_prob
        """,
            (date, date, regime, final_score, target_exposure, posterior_prob),
        )
        conn.commit()


def upsert_indicator_scores(date: str, scores: Dict[str, float], db_path=DEFAULT_DB_PATH):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        for indicator_name, score in scores.items():
            cursor.execute(
                """
                INSERT INTO indicator_scores (date, indicator_name, score)
                VALUES (?, ?, ?)
                ON CONFLICT(date, indicator_name) DO UPDATE SET
                    score = excluded.score
            """,
                (date, indicator_name, score),
            )
        conn.commit()


def log_regime_transition(
    transition_date: str,
    previous_regime: Optional[str],
    new_regime: str,
    posterior_probability: Optional[float],
    triggering_metrics: Optional[str] = None,
    db_path=DEFAULT_DB_PATH,
):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO regime_transitions (transition_date, previous_regime, new_regime, posterior_probability, triggering_metrics)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(transition_date) DO UPDATE SET
                previous_regime = excluded.previous_regime,
                new_regime = excluded.new_regime,
                posterior_probability = excluded.posterior_probability,
                triggering_metrics = excluded.triggering_metrics
        """,
            (
                transition_date,
                previous_regime,
                new_regime,
                posterior_probability,
                triggering_metrics,
            ),
        )
        conn.commit()


def upsert_pca_components(date: str, components: dict, db_path=DEFAULT_DB_PATH):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        for component_name, value in components.items():
            cursor.execute(
                """
                INSERT INTO pca_components (date, component_name, value)
                VALUES (?, ?, ?)
                ON CONFLICT(date, component_name) DO UPDATE SET
                    value = excluded.value
            """,
                (date, component_name, value),
            )
        conn.commit()
