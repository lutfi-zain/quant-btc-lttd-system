import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import vectorbt as vbt
import sys
import os

# Ensure project root in PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.pipeline import ohlcv_pipeline
from src.signals.onchain import OnChainFeed
from src.backtest.wfo import point_in_time_join
from src.backtest.runner import BacktestRunner

def main():
    print("Loading OHLCV...")
    df_ohlcv = ohlcv_pipeline()
    
    print("Loading On-chain data...")
    feed = OnChainFeed()
    # Fetch 5500 days (~15 years) to ensure we have data from 2011
    onchain = feed.fetch_historical_bulk(start=-5500)
    
    print("Joining datasets...")
    df_merged = point_in_time_join(df_ohlcv, onchain)
    
    # Filter range starting from 2012 to give WFO 3.5 years of warmup before 2016
    df_merged = df_merged.loc["2012-01-01":]
    print(f"Data rows: {len(df_merged)}")
    
    runner = BacktestRunner(legacy_fixed_window=False, ensemble_mode="pca_consensus")
    print("Running Backtest WFO...")
    res = runner.run(df_merged)
    
    results_df = res["results"]
    
    # Strictly limit the final plotted data to start exactly from 2016
    results_df = results_df.loc["2016-01-01":]
    
    # Run Portfolio to get Equity Curve
    print("Calculating Equity Curve...")
    close_series = results_df["close"]
    exposure = results_df["target_exposure"]
    
    portfolio = vbt.Portfolio.from_orders(
        close_series,
        size=exposure,
        size_type='targetpercent',
        init_cash=10000.0,
        fees=0.001
    )
    equity_curve = portfolio.value()
    
    print("Generating Interactive HTML Chart...")
    # Get OHLC data matched with results index
    ohlc = df_merged.loc[results_df.index]
    
    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.4, 0.2, 0.2, 0.2],
        subplot_titles=(
            "Bitcoin OHLC",
            "LTTD Oscillator Score (Consensus)",
            "Capital Position % (Target Exposure)",
            "System Equity Curve ($)"
        )
    )
    
    # 1. OHLC
    fig.add_trace(go.Candlestick(
        x=ohlc.index,
        open=ohlc['open'],
        high=ohlc['high'],
        low=ohlc['low'],
        close=ohlc['close'],
        name="BTC/USD"
    ), row=1, col=1)
    
    # 2. Oscillator
    # Extract final score from raw records since results_df has final_score.
    final_score = results_df["final_score"]
    fig.add_trace(go.Scatter(
        x=results_df.index,
        y=final_score,
        mode="lines",
        line=dict(color='purple', width=2),
        name="Final Score"
    ), row=2, col=1)
    
    # Add horizontal lines for regimes
    fig.add_hline(y=0.8, line_dash="dash", line_color="green", row=2, col=1, annotation_text="Strong Bull (1.0)")
    fig.add_hline(y=0.6, line_dash="dash", line_color="lightgreen", row=2, col=1, annotation_text="Weak Bull (0.5)")
    fig.add_hline(y=0.4, line_dash="dash", line_color="orange", row=2, col=1, annotation_text="Neutral (0.0)")
    fig.add_hline(y=0.2, line_dash="dash", line_color="red", row=2, col=1, annotation_text="Weak Bear (0.0)")
    
    # 3. Target Exposure
    fig.add_trace(go.Scatter(
        x=results_df.index,
        y=exposure * 100, # to percentage
        mode="lines",
        line=dict(color='blue', width=2, shape='hv'), # step line
        fill='tozeroy',
        name="Position %"
    ), row=3, col=1)
    
    # 4. Equity Curve
    fig.add_trace(go.Scatter(
        x=equity_curve.index,
        y=equity_curve,
        mode="lines",
        line=dict(color='gold', width=2),
        name="Equity ($)"
    ), row=4, col=1)
    # Buy and hold eq for benchmark
    bnh = (close_series / close_series.iloc[0]) * 10000.0
    fig.add_trace(go.Scatter(
        x=bnh.index,
        y=bnh,
        mode="lines",
        line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dot'),
        name="Buy & Hold"
    ), row=4, col=1)
    
    # Layout adjustments
    fig.update_layout(
        title="LTTD Quantitative Trading System - Performance Overview",
        xaxis_rangeslider_visible=False,
        height=1200,
        template="plotly_dark",
        showlegend=True
    )
    
    # Optional: Format axes
    fig.update_yaxes(title_text="Price ($)", type="log", row=1, col=1)
    fig.update_yaxes(title_text="Score", range=[0, 1], row=2, col=1)
    fig.update_yaxes(title_text="Exposure (%)", range=[0, 105], row=3, col=1)
    fig.update_yaxes(title_text="Equity ($)", type="log", row=4, col=1)
    
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backtest_chart.html"))
    fig.write_html(output_path)
    print(f"Chart successfully saved to {output_path}")

if __name__ == '__main__':
    main()
