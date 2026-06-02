# ============================================================
# MAIN LOOP
# Run this once. It polls forever on POLL_INTERVAL_SECONDS,
# detects significant changes, and rewrites the summary when needed.
# The jumbotron display page reads summary.json automatically.
#
# To run:  python main.py
# To stop: Ctrl+C
# ============================================================

import os
import json
import time
import traceback
from datetime import datetime

from config import POLL_INTERVAL_SECONDS, SUMMARY_OUTPUT, OPERATING_HOURS, DAILY_SPEND_LIMIT, COST_PER_API_CALL
from data_fetcher import fetch_latest
from change_detector import should_rewrite, format_score_label
from summarizer import generate_summary


def run():
    print("=" * 60)
    print("  Alltech Jumbotron Monitor")
    print(f"  Polling every {POLL_INTERVAL_SECONDS // 60} min | Output: {SUMMARY_OUTPUT}")
    print("=" * 60)

    last_fetch = None
    cycle = 0
    _daily_calls = 0 #simple counter to track API calls for stop loss

    while True:
        cycle += 1
        print(f"\n[{time.strftime('%H:%M:%S')}] Cycle {cycle}")

        hour = datetime.now().hour
        if not (OPERATING_HOURS[0] <= hour < OPERATING_HOURS[1]):
            print("  Outside operating hours, sleeping...")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if _daily_calls * COST_PER_API_CALL >= DAILY_SPEND_LIMIT:
            print(f"  Daily spend limit reached ({_daily_calls} calls), skipping AI")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue


        try:
            # 1. Pull latest data
            current_fetch = fetch_latest()

            if current_fetch is None:
                print("  No data available yet. Waiting...")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            print(f"  Source: {current_fetch['source_label']}")

            # 2. Decide whether to rewrite
            trigger, score = should_rewrite(current_fetch, last_fetch)
            label = format_score_label(score)
            print(f"  Change score: {score:.3f} ({label})")

            if trigger:
                print("  → Running AI analysis...")
                summary = generate_summary(current_fetch)
                _daily_calls += 1

                # Attach metadata
                summary["last_updated"]  = time.strftime("%Y-%m-%d %H:%M:%S")
                summary["source_label"]  = current_fetch["source_label"]
                summary["source_type"]   = current_fetch["source_type"]
                summary["change_score"]  = score
                summary["change_label"]  = label
                summary["poll_cycle"]    = cycle

                _write_summary(summary)
                print(f"  ✓ Summary updated: {summary.get('headline', '—')}")
                print(f"  ✓ Rating: {summary.get('performance_rating', '—')}")
            else:
                # Even with no AI rewrite, update the timestamp so the
                # display knows the system is still alive
                _touch_summary(cycle)
                print("  → No significant change, skipping AI call")

            last_fetch = current_fetch

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()

        print(f"  Sleeping {POLL_INTERVAL_SECONDS // 60} min...")
        time.sleep(POLL_INTERVAL_SECONDS)


def _write_summary(summary):
    os.makedirs(os.path.dirname(SUMMARY_OUTPUT), exist_ok=True)
    with open(SUMMARY_OUTPUT, "w") as f:
        json.dump(summary, f, indent=2)


def _touch_summary(cycle):
    """Update just the heartbeat fields without overwriting the summary."""
    try:
        with open(SUMMARY_OUTPUT) as f:
            data = json.load(f)
        data["last_checked"] = time.strftime("%Y-%m-%d %H:%M:%S")
        data["poll_cycle"] = cycle
        with open(SUMMARY_OUTPUT, "w") as f:
            json.dump(data, f, indent=2)
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # no summary yet, that's fine


if __name__ == "__main__":
    run()
