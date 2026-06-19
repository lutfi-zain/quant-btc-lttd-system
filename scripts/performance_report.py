#!/usr/bin/env python3
"""
Performance Report — LTTD System
Read-only analysis from lttd.db. No writes.
Usage: python3 tmp/performance_report.py
"""

import sqlite3
import sys
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

DB = Path("database/lttd.db")


def connect():
    if not DB.exists():
        print(f"[ERR] DB not found: {DB}")
        sys.exit(1)
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    return conn


def sim_equity(signals: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate equity curve from daily signals.
    - Position = target_exposure
    - Daily return = position.shift(1) * simple_return
    """
    df = signals.copy().sort_values("date")
    df["position"] = df["target_exposure"].abs()
    df["strat_return"] = df["position"].shift(1) * df["simple_return"]
    df["strat_return"] = df["strat_return"].fillna(0.0)
    df["equity"] = (1 + df["strat_return"]).cumprod()
    return df


def annual_sharpe(r: pd.Series, rf: float = 0.0) -> float:
    excess = r - rf / 365
    if excess.std() == 0 or excess.count() < 10:
        return 0.0
    return float(np.sqrt(365) * excess.mean() / excess.std())


def max_dd(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min())


def cagr(equity: pd.Series, years: float) -> float:
    if years <= 0 or equity.iloc[0] <= 0:
        return 0.0
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)

def annual_sortino(r: pd.Series, rf: float = 0.0) -> float:
    excess = r - rf / 365
    downside = excess[excess < 0]
    if len(downside) < 5 or downside.std() == 0:
        return 0.0
    return float(np.sqrt(365) * excess.mean() / downside.std())


def trade_stats(df: pd.DataFrame) -> dict:
    """Extract trade-level stats from contiguous non-zero position periods."""
    df_temp = df.copy()
    df_temp["in_pos"] = df_temp["position"] > 0
    # True where trade starts
    starts = df_temp.index[(df_temp["in_pos"]) & (~df_temp["in_pos"].shift(1).fillna(False))].tolist()
    # True where trade ends (first day of 0 position after a trade)
    ends = df_temp.index[(~df_temp["in_pos"]) & (df_temp["in_pos"].shift(1).fillna(False))].tolist()
    
    if len(starts) > len(ends):
        ends.append(df_temp.index[-1])
        
    trades = []
    for s, e in zip(starts, ends):
        s_idx = df_temp.index.get_loc(s)
        e_idx = df_temp.index.get_loc(e)
        # Compounding daily returns: (1 + strat_return).prod() - 1
        tr = (1 + df_temp["strat_return"].iloc[s_idx+1 : e_idx+1]).prod() - 1
        trades.append(tr)
        
    if not trades:
        return {"trades": 0, "win_rate": 0, "profit_factor": 0, "avg_win_pct": 0, "avg_loss_pct": 0}
        
    wins = [tr for tr in trades if tr > 0]
    losses = [tr for tr in trades if tr <= 0]
    w_rate = len(wins) / len(trades) if trades else 0
    p_factor = (
        sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else float("inf")
    )
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    return {
        "trades": len(trades),
        "win_rate": w_rate,
        "profit_factor": p_factor,
        "avg_win_pct": avg_win * 100,
        "avg_loss_pct": avg_loss * 100,
    }


def regime_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Performance by regime."""
    groups = []
    for regime, grp in df.groupby("regime"):
        if grp["strat_return"].count() < 5:
            continue
        grp = grp.reset_index(drop=True)
        eq = (1 + grp["strat_return"]).cumprod()
        strat_r = cast(pd.Series, grp["strat_return"])
        groups.append(
            {
                "regime": regime,
                "days": len(grp),
                "total_return": float(eq.iloc[-1] - 1) * 100,
                "avg_daily_return": float(strat_r.mean()) * 100,
                "sharpe": annual_sharpe(strat_r),
                "max_dd_pct": max_dd(cast(pd.Series, eq)) * 100,
            }
        )
    return (
        pd.DataFrame(groups).sort_values("days", ascending=False)
        if groups
        else pd.DataFrame()
    )


def main():
    conn = connect()
    print("=" * 58)
    print("  LTTD System — Performance Report  ")
    print("=" * 58)

    # ── Check data ──────────────────────────────────────────────
    lttd = pd.read_sql("SELECT count(*) AS n FROM daily_lttd", conn)
    if lttd.n[0] == 0:
        print("\n[!] daily_lttd empty. Pipeline belum pernah jalan.")
        print("    Jalankan dulu:  python3 backfill_all.py")
        print("    atau:           python3 backfill.py")
        print("\n    Tapi dengan ohlcv ada, bisa liat price overview doang.\n")
        _price_overview(conn)
        conn.close()
        return

    # ── Load data ───────────────────────────────────────────────
    df = pd.read_sql(
        """
        SELECT
            d.date,
            d.regime,
            d.final_score,
            d.target_exposure,
            d.posterior_prob,
            d.circuit_breaker_active,
            o.close
        FROM daily_lttd d
        JOIN ohlcv o ON DATE(o.timestamp) = d.date
        ORDER BY d.date
    """,
        conn,
        parse_dates=["date"],
    )

    if df.empty:
        print("[!] daily_lttd ada isi tapi gak ada join match dgn ohlcv.")
        conn.close()
        return

    df["simple_return"] = df["close"].pct_change()
    df = df.dropna(subset=["simple_return"]).reset_index(drop=True)

    # ── Simulate ────────────────────────────────────────────────
    eq_df = sim_equity(df)
    years = (eq_df["date"].max() - eq_df["date"].min()).days / 365.25

    # ── Metrics ─────────────────────────────────────────────────
    strat_r = cast(pd.Series, eq_df["strat_return"])
    equity_s = cast(pd.Series, eq_df["equity"])
    sharpe = annual_sharpe(strat_r)
    sortino = annual_sortino(strat_r)
    dd_pct = max_dd(equity_s) * 100
    cagr_val = cagr(equity_s, years) * 100
    calmar = cagr_val / abs(dd_pct) if dd_pct != 0 else float("inf")

    print(
        f"\n  Periode    : {df['date'].min().date()} → {df['date'].max().date()}  ({years:.1f} thn)"
    )
    print(f"  Trading    : {len(df)} hari")
    print("\n  ╔═════════════════════════════════════╗")
    print(f"  ║  RETURN      {cagr_val:>8.2f}%  CAGR         ║")
    print(f"  ║  SHARPE      {sharpe:>8.2f}               ║")
    print(f"  ║  SORTINO     {sortino:>8.2f}               ║")
    print(f"  ║  MAX DD      {dd_pct:>8.2f}%               ║")
    print(f"  ║  CALMAR      {calmar:>8.2f}               ║")
    print("  ╚═════════════════════════════════════╝")

    # ── Circuit Breaker stats ──────────────────────────────────
    if "circuit_breaker_active" in df.columns:
        cb_days = df["circuit_breaker_active"].sum()
        if cb_days > 0:
            print(f"\n  [!] Circuit Breaker Active: {int(cb_days)} days")

    # ── Trade stats ────────────────────────────────────────────
    ts = trade_stats(eq_df)
    if ts["trades"] > 0:
        print(f"\n  Trades     : {ts['trades']}")
        print(f"  Win Rate   : {ts['win_rate'] * 100:.1f}%")
        print(f"  Profit Fac : {ts['profit_factor']:.2f}")
        print(f"  Avg Win    : {ts['avg_win_pct']:.2f}%")
        print(f"  Avg Loss   : {ts['avg_loss_pct']:.2f}%")

    # ── Regime breakdown ───────────────────────────────────────
    rb = regime_breakdown(eq_df)
    if not rb.empty:
        print("\n  ── Regime Breakdown ──")
        for _, r in rb.iterrows():
            print(
                f"  {r['regime']:<12}  {r['days']:>5}d  "
                f"ret {r['total_return']:>7.2f}%  "
                f"sharpe {r['sharpe']:>5.2f}  "
                f"maxDD {r['max_dd_pct']:>6.2f}%"
            )

    # ── Signal distribution ────────────────────────────────────
    print("\n  ── Score Distribution ──")
    bins = [-1.1, -0.5, -0.1, 0.1, 0.5, 1.1]
    labels = ["Strong Sell", "Sell", "Neutral", "Buy", "Strong Buy"]
    eq_df["signal_bin"] = pd.cut(eq_df["final_score"], bins=bins, labels=labels)
    dist = eq_df["signal_bin"].value_counts()
    for lb in labels:
        print(f"  {lb:<14} {dist.get(lb, 0):>6} days")

    # ── Yearly breakdown ───────────────────────────────────────
    eq_df["year"] = eq_df["date"].dt.year
    yearly = eq_df.groupby("year").apply(
        lambda g: pd.Series(
            {
                "return_pct": (1 + cast(pd.Series, g["strat_return"])).prod() - 1,
                "sharpe": annual_sharpe(cast(pd.Series, g["strat_return"])),
                "days": len(g),
            }
        ),
        include_groups=False,
    )
    print("\n  ── Yearly Returns ──")
    print(f"  {'Year':>6}  {'Return':>8}  {'Sharpe':>7}  {'Days':>5}")
    for yr, row in yearly.iterrows():
        ret = row["return_pct"]
        ret_s = f"{ret * 100:>7.2f}%"
        yr_int = int(cast(int, yr))
        print(f"  {yr_int:>6}  {ret_s}  {row['sharpe']:>7.2f}  {int(row['days']):>5d}")

    # ── Monthly heatmap (text) ──────────────────────────────────
    eq_df["month"] = eq_df["date"].dt.month
    monthly = (
        cast(pd.Series, eq_df.groupby(["year", "month"])["strat_return"].sum()) * 100
    )
    print("\n  ── Monthly Returns (%) ──")
    print("  ", " ".join(f"{m:>6}" for m in range(1, 13)))
    for yr in sorted(eq_df["year"].unique()):
        row_data = [monthly.get((yr, m), 0) for m in range(1, 13)]
        row_str = " ".join(f"{v:>6.1f}" for v in row_data)
        print(f"  {cast(int, yr)} {row_str}")

    conn.close()
    print("\n✅ Done.")


def _price_overview(conn):
    """Show basic BTC price stats when no signals exist."""
    df = pd.read_sql(
        "SELECT timestamp, close FROM ohlcv ORDER BY timestamp",
        conn,
        parse_dates=["timestamp"],
    )
    if df.empty:
        print("[!] ohlcv juga kosong.")
        return
    price_now = df["close"].iloc[-1]
    price_first = df["close"].iloc[0]
    daily_ret = cast(pd.Series, np.log(df["close"] / df["close"].shift(1)).dropna())
    sharpe_price = annual_sharpe(daily_ret)
    close_s = cast(pd.Series, df["close"])
    dd_price = max_dd(close_s) * 100
    years = (df["timestamp"].max() - df["timestamp"].min()).days / 365.25
    cagr_price = ((price_now / price_first) ** (1 / years) - 1) * 100
    print(f"  BTC Price Overview  ({years:.1f} yr)")
    print(
        f"    Periode  : {df['timestamp'].min().date()} → {df['timestamp'].max().date()}"
    )
    print(f"    Close    : ${price_now:,.2f}  (first ${price_first:,.2f})")
    print(f"    CAGR     : {cagr_price:.2f}%")
    print(f"    Sharpe   : {sharpe_price:.2f}")
    print(f"    Max DD   : {dd_price:.2f}%")


if __name__ == "__main__":
    main()
