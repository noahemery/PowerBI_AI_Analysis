# ============================================================
# CHANGE DETECTOR
# Compares the current data snapshot to the last one.
# Returns a score 0.0–1.0. Anything above CHANGE_THRESHOLD
# in config.py triggers a Claude rewrite.
# ============================================================

import os
import time
from config import CHANGE_THRESHOLD


KEY_METRICS = [
    "bfw_avg",
    "oee_avg",
    "loading_time_avg",
    "loaded_vs_expected",
    "bag_hang_success_avg",
]


def should_rewrite(current_fetch, last_fetch):
    """
    Returns (bool, float) — (trigger_rewrite, change_score).
    """
    # Don't auto-trigger on startup if we already have a summary for this file
    if last_fetch is None:
        import os, json
        from config import SUMMARY_OUTPUT
        if os.path.exists(SUMMARY_OUTPUT):
            try:
                with open(SUMMARY_OUTPUT) as f:
                    existing = json.load(f)
                if existing.get("source_label") == current_fetch.get("source_label"):
                    return False, 0.0
            except:
                pass
        return True, 1.0

    score = _calculate_score(current_fetch, last_fetch)
    return score > CHANGE_THRESHOLD, round(score, 4)


def _calculate_score(current, last):
    source = current.get("source_type")

    # PDF mode: use file modification time as the signal.
    # A new file = score 1.0. Same file, same mtime = score 0.0.
    if source == "pdf":
        curr_meta = current.get("_meta", {})
        last_meta = last.get("_meta", {})
        if curr_meta.get("path") != last_meta.get("path"):
            return 1.0   # new file dropped
        if curr_meta.get("mtime", 0) != last_meta.get("mtime", 0):
            return 0.8   # same file but modified
        return 0.0

    # Structured data (database / CSV / API): compare metric values.
    curr_struct = current.get("structured") or {}
    last_struct = last.get("structured") or {}

    if not curr_struct or not last_struct:
        return 1.0   # can't compare — assume significant

    changes = []
    for metric in KEY_METRICS:
        old_val = last_struct.get(metric, 0)
        new_val = curr_struct.get(metric, 0)
        if old_val and old_val != 0:
            changes.append(abs(new_val - old_val) / abs(old_val))

    return max(changes) if changes else 0.0


def format_score_label(score):
    if score >= 0.5:
        return "major shift"
    elif score >= 0.1:
        return "notable change"
    elif score > 0:
        return "minor drift"
    return "no change"
