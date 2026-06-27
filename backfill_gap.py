"""
Smart Gap Backfill Script for LTTD System.

Detects the latest date in the database, calculates the gap to today,
and runs LTTDPipeline.run_daily() sequentially for each missing date.

Usage:
    python backfill_gap.py                    # Interactive mode (prompts for confirmation)
    python backfill_gap.py --non-interactive  # API mode (no prompts, auto-proceeds)
"""

import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

# Ensure current directory is in python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.execution.database import init_db, DEFAULT_DB_PATH, get_connection
from src.pipeline import LTTDPipeline, DataStaleException


MAX_GAP_WARNING_DAYS = 90


def detect_gap(db_path: str = DEFAULT_DB_PATH) -> tuple:
    """
    Query the daily_lttd table for the most recent date.
    
    Returns:
        (last_date: datetime | None, gap_days: int)
        - last_date is None if the database is empty
        - gap_days is the number of missing days between last_date and today (UTC)
    """
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) as max_date FROM daily_lttd")
            row = cursor.fetchone()
            
            if row is None or row["max_date"] is None:
                return None, 0
            
            max_date_str = row["max_date"]
            last_date = datetime.strptime(max_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            
            gap_days = (today - last_date).days
            return last_date, gap_days
    except Exception as e:
        print(f"Error querying database: {e}")
        return None, 0


def check_valuation_api(timeout: float = 3.0) -> bool:
    """
    Check if quant-btc-valuation-system is running by hitting its composite endpoint.
    
    Returns:
        True if the API is reachable, False otherwise.
    """
    import requests
    try:
        resp = requests.get("http://localhost:5173/api/composite", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Smart gap backfill for LTTD system")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip all confirmation prompts (for API/automated mode)"
    )
    args = parser.parse_args()
    
    interactive = not args.non_interactive
    db_path = DEFAULT_DB_PATH
    
    print("==========================================================================")
    print("            LTTD SYSTEM - SMART GAP BACKFILL                              ")
    print("==========================================================================")
    
    # Initialize database
    init_db(db_path)
    
    # Step 1: Detect the gap
    print("\nDetecting data gap...")
    last_date, gap_days = detect_gap(db_path)
    
    if last_date is None:
        print("✗ Database is empty. Run backfill_all.py first.")
        sys.exit(1)
    
    if gap_days <= 0:
        print(f"✓ Database is already up to date (latest: {last_date.strftime('%Y-%m-%d')}).")
        sys.exit(0)
    
    # Calculate missing date range
    missing_dates = []
    for i in range(1, gap_days + 1):
        missing_dates.append(last_date + timedelta(days=i))
    
    print(f"Found gap: {gap_days} days ({missing_dates[0].strftime('%Y-%m-%d')} → {missing_dates[-1].strftime('%Y-%m-%d')})")
    
    # Step 2: Check valuation API health
    print("\nChecking quant-btc-valuation-system API...")
    valuation_ok = check_valuation_api()
    
    if not valuation_ok:
        print("⚠️  quant-btc-valuation-system is not running. Circuit breaker will be disabled (composite defaults to 0.0).")
        if interactive:
            answer = input("Continue anyway? (y/N): ").strip().lower()
            if answer != "y":
                print("Aborted by user.")
                sys.exit(0)
        else:
            print("   (non-interactive mode: proceeding with warning)")
    else:
        print("✓ Valuation API is healthy.")
    
    # Step 3: Safety check for large gaps
    if gap_days > MAX_GAP_WARNING_DAYS:
        print(f"\n⚠️  Gap is {gap_days} days (> {MAX_GAP_WARNING_DAYS}). For large gaps, consider running backfill_all.py instead.")
        if interactive:
            answer = input("Continue anyway? (y/N): ").strip().lower()
            if answer != "y":
                print("Aborted by user.")
                sys.exit(0)
        else:
            print("   (non-interactive mode: proceeding with warning)")
    
    # Step 4: Sequential gap fill
    print(f"\nStarting gap fill for {len(missing_dates)} dates...")
    print("==========================================================================")
    
    pipeline = LTTDPipeline()
    
    successful = []
    failed = []
    
    total = len(missing_dates)
    for i, target_date in enumerate(missing_dates, 1):
        date_str = target_date.strftime("%Y-%m-%d")
        try:
            res = pipeline.run_daily(target_date)
            regime = res.get("regime", "?")
            score = res.get("final_score", 0.0)
            exposure = res.get("target_exposure", 0.0)
            print(f"[{i}/{total}] {date_str}: {regime} (Score: {score:.4f}, Exposure: {exposure:.1f})")
            successful.append(date_str)
        except DataStaleException as e:
            print(f"[{i}/{total}] {date_str}: SKIPPED (stale data) - {e}")
            failed.append((date_str, f"stale data: {e}"))
        except Exception as e:
            print(f"[{i}/{total}] {date_str}: ERROR - {e}")
            failed.append((date_str, str(e)))
    
    # Step 5: Final summary
    print("\n==========================================================================")
    print(f"Completed: {len(successful)}/{total} successful, {len(failed)} failed")
    
    if failed:
        print("\nFailed dates:")
        for date_str, reason in failed:
            print(f"  - {date_str}: {reason}")
    
    if len(successful) == total:
        print("\n✓ GAP BACKFILL COMPLETED SUCCESSFULLY!")
    elif len(successful) > 0:
        print("\n⚠️  Gap backfill completed with some failures.")
    else:
        print("\n✗ Gap backfill failed completely.")
    
    print("==========================================================================")
    sys.exit(0 if len(failed) == 0 else 1)


if __name__ == "__main__":
    main()
