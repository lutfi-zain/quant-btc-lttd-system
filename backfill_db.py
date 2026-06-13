import pandas as pd
from src.backtest.runner import BacktestRunner
from src.data.pipeline import ohlcv_pipeline
import sqlite3

def run():
    print("Loading data...")
    df = ohlcv_pipeline()
    
    print("Running WFO Backtest...")
    runner = BacktestRunner(legacy_fixed_window=False)
    res = runner.run(df)
    records = res["raw_records"]
    
    # Drop duplicates by date
    unique_records = {r['date'].strftime("%Y-%m-%d"): r for r in records}
    
    print("Updating database...")
    conn = sqlite3.connect("database/lttd.db")
    c = conn.cursor()
    
    c.execute("DELETE FROM daily_lttd")
    c.execute("DELETE FROM indicator_scores")
    c.execute("DELETE FROM pca_components")
    
    for date_str, r in unique_records.items():
        c.execute("""
            INSERT INTO daily_lttd (date, regime, final_score, target_exposure, posterior_prob)
            VALUES (?, ?, ?, ?, ?)
        """, (date_str, r['regime'], float(r['final_score']), float(r['target_exposure']), str(r['posteriors'])))
        
        for ind, score in r['indicator_scores'].items():
            c.execute("INSERT INTO indicator_scores (date, indicator_name, score) VALUES (?, ?, ?)",
                     (date_str, ind, float(score)))
                     
        for comp, val in r['pca_components'].items():
            c.execute("INSERT INTO pca_components (date, component_name, value) VALUES (?, ?, ?)",
                     (date_str, comp, float(val)))
                     
    conn.commit()
    conn.close()
    print("Database updated successfully!")

if __name__ == "__main__":
    run()
