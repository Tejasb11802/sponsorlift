r"""
Converts simulated exposure events into a quality-adjusted media value,
mirroring the factor-based approach Zoomph describes publicly (clarity,
size, centrality, clutter, duration -> equivalent media value via a
CPM-style rate).

Quality-adjusted seconds = duration_seconds * clarity * centrality * (1 - clutter)
    -- a raw second of exposure that's small, blurry, off-center, or
    cluttered with other graphics counts for less than a clean, large,
    centered, uncluttered second. The weights here are a simplified
    illustration of the concept, not a calibrated model -- a real
    version would be fit against verified impression/recall data.

Equivalent Media Value = (quality-adjusted seconds / 30) * CPM_RATE * (avg_audience / 1000)
    -- treats each 30 "quality-adjusted seconds" as roughly equivalent to
    one :30 TV spot, priced at the given CPM against the average audience.
    CPM_RATE is a placeholder assumption (see below), not a licensed
    ad-rate benchmark -- swap in a real rate card for production use.

Run:
    python src\valuation_engine.py
"""

import os
import pandas as pd

IN_PATH = os.path.join("data", "raw", "exposure_events_simulated.csv")
OUT_PATH = os.path.join("data", "processed", "broadcast_valuation.csv")

# ---- ASSUMPTIONS (documented, adjustable) ----
CPM_RATE = 28.0                      # illustrative national TV CPM in USD; not a sourced benchmark
AVG_BROADCAST_AUDIENCE = 1_800_000   # illustrative average live viewers per broadcast


def main():
    if not os.path.exists(IN_PATH):
        raise SystemExit(f"{IN_PATH} not found. Run src\\generate_exposure_events.py first.")

    df = pd.read_csv(IN_PATH)

    df["quality_adjusted_seconds"] = (
        df["duration_seconds"] * df["clarity"] * df["centrality"] * (1 - df["clutter"])
    )

    per_broadcast = df.groupby("broadcast_id").agg(
        sponsor=("sponsor", "first"),
        n_appearances=("appearance_id", "count"),
        raw_exposure_seconds=("duration_seconds", "sum"),
        quality_adjusted_seconds=("quality_adjusted_seconds", "sum"),
    ).reset_index()

    per_broadcast["avg_audience"] = AVG_BROADCAST_AUDIENCE
    per_broadcast["equivalent_media_value_usd"] = (
        (per_broadcast["quality_adjusted_seconds"] / 30)
        * CPM_RATE
        * (per_broadcast["avg_audience"] / 1000)
    ).round(2)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    per_broadcast.to_csv(OUT_PATH, index=False)

    total_value = per_broadcast["equivalent_media_value_usd"].sum()
    print(per_broadcast.to_string(index=False))
    print(f"\nTotal simulated media value across {len(per_broadcast)} broadcasts: ${total_value:,.2f}")
    print(f"Saved to {OUT_PATH}")
    print(
        "\nNote: CPM_RATE and AVG_BROADCAST_AUDIENCE are illustrative "
        "placeholders, not sourced benchmarks. Swap them for a real rate "
        "card and verified audience data in production."
    )


if __name__ == "__main__":
    main()