r"""
Simulates broadcast-level sponsor exposure events (jersey patch logo
appearances) for a set of broadcasts, using documented, adjustable
assumptions about placement frequency, duration, and visual quality
factors. This is SIMULATED data, not real detection output -- Zoomph's
actual computer-vision detection data isn't publicly available. The
assumptions are intentionally exposed as parameters at the top of this
file so they're auditable rather than buried, which is the same
"defensible methodology" bar the real thing has to meet.

Run:
    python src\generate_exposure_events.py
"""

import os
import numpy as np
import pandas as pd

np.random.seed(7)  # reproducible for demo purposes

# ---- ASSUMPTIONS (documented, adjustable) ----
# Illustrative, not sourced from real detection data or a published
# industry benchmark. In production this table would be replaced by
# actual computer-vision detection output.
BROADCAST_LENGTH_MINUTES = 150
N_BROADCASTS = 12
APPEARANCES_PER_BROADCAST_RANGE = (18, 40)
DURATION_SECONDS_RANGE = (1, 8)
SIZE_PCT_RANGE = (0.3, 2.5)
CLARITY_RANGE = (0.4, 1.0)
CENTRALITY_RANGE = (0.1, 1.0)
CLUTTER_RANGE = (0.0, 0.6)

SPONSOR = "IREN Limited"
BROADCAST_IDS = [f"GSW_2026_G{n+1:02d}" for n in range(N_BROADCASTS)]


def simulate_broadcast(broadcast_id):
    n_appearances = np.random.randint(*APPEARANCES_PER_BROADCAST_RANGE)
    start_minutes = np.sort(np.random.uniform(0, BROADCAST_LENGTH_MINUTES, n_appearances))
    rows = []
    for i, start_minute in enumerate(start_minutes):
        rows.append({
            "broadcast_id": broadcast_id,
            "sponsor": SPONSOR,
            "appearance_id": f"{broadcast_id}_A{i+1:03d}",
            "start_minute": round(float(start_minute), 2),
            "duration_seconds": round(float(np.random.uniform(*DURATION_SECONDS_RANGE)), 2),
            "size_pct": round(float(np.random.uniform(*SIZE_PCT_RANGE)), 2),
            "clarity": round(float(np.random.uniform(*CLARITY_RANGE)), 2),
            "centrality": round(float(np.random.uniform(*CENTRALITY_RANGE)), 2),
            "clutter": round(float(np.random.uniform(*CLUTTER_RANGE)), 2),
        })
    return rows


def main():
    all_rows = []
    for broadcast_id in BROADCAST_IDS:
        all_rows.extend(simulate_broadcast(broadcast_id))

    df = pd.DataFrame(all_rows)
    out_path = os.path.join("data", "raw", "exposure_events_simulated.csv")
    df.to_csv(out_path, index=False)
    print(f"Simulated {len(df)} exposure events across {N_BROADCASTS} broadcasts")
    print(f"Saved to {out_path}")
    print(df.groupby("broadcast_id")["duration_seconds"].agg(["count", "sum"]).rename(
        columns={"count": "n_appearances", "sum": "total_raw_seconds"}
    ))


if __name__ == "__main__":
    main()