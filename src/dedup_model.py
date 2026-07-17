r"""
Cross-screen reach deduplication: combines broadcast audience reach with
social video reach and estimates a deduplicated (unique) combined reach,
correcting for the fact that summing both channels' reach numbers
double-counts people who saw the sponsor on both broadcast and social.

This is the hardest, least "solvable from public data" piece of the
pipeline -- real deduplication requires a cross-platform identity graph
(device IDs, login data, panel matching) that isn't available outside a
company like Zoomph. What's implemented here is an illustrative overlap
model with the assumption exposed as a parameter, swept across a
plausible range rather than presented as one precise number.

Run:
    python src\dedup_model.py
"""

import os
import pandas as pd

VALUATION_PATH = os.path.join("data", "processed", "broadcast_valuation.csv")
SOCIAL_PATH = os.path.join("data", "raw", "youtube_video_stats.csv")
OUT_PATH = os.path.join("data", "processed", "cross_screen_reach.csv")

# ---- ASSUMPTIONS (documented, adjustable) ----
# Fraction of the smaller reach pool assumed to have also seen the sponsor
# on the other screen. In production this would come from a panel-based
# identity graph, not an assumed constant. We sweep a range instead of
# picking one number, to show how sensitive the "unique reach" claim is
# to an assumption most public-facing dashboards don't expose.
OVERLAP_RATE_SCENARIOS = {"low_overlap": 0.10, "mid_overlap": 0.25, "high_overlap": 0.45}

# Average-minute broadcast audience understates unique reach because
# viewers tune in and out over a live game. This turnover multiplier
# converts average audience to an estimated unique/cume reach.
# Illustrative assumption, not a sourced Nielsen figure.
AUDIENCE_TURNOVER_MULTIPLIER = 1.4


def main():
    if not os.path.exists(VALUATION_PATH):
        raise SystemExit(f"{VALUATION_PATH} not found. Run src\\valuation_engine.py first.")
    if not os.path.exists(SOCIAL_PATH):
        raise SystemExit(f"{SOCIAL_PATH} not found. Run src\\ingest_youtube.py first.")

    valuation_df = pd.read_csv(VALUATION_PATH)
    social_df = pd.read_csv(SOCIAL_PATH)

    broadcast_avg_audience = valuation_df["avg_audience"].iloc[0]
    broadcast_reach = broadcast_avg_audience * AUDIENCE_TURNOVER_MULTIPLIER

    post_event_treatment = social_df[
        (social_df["group"] == "treatment") & (social_df["is_post_event"])
    ]
    social_reach = post_event_treatment["view_count"].sum()

    rows = []
    for scenario_name, overlap_rate in OVERLAP_RATE_SCENARIOS.items():
        smaller_pool = min(broadcast_reach, social_reach)
        estimated_overlap = smaller_pool * overlap_rate
        naive_summed_reach = broadcast_reach + social_reach
        deduplicated_reach = naive_summed_reach - estimated_overlap
        overstatement_pct = (estimated_overlap / naive_summed_reach) * 100

        rows.append({
            "scenario": scenario_name,
            "assumed_overlap_rate": overlap_rate,
            "broadcast_reach": round(broadcast_reach),
            "social_reach": round(social_reach),
            "naive_summed_reach": round(naive_summed_reach),
            "estimated_overlap": round(estimated_overlap),
            "deduplicated_unique_reach": round(deduplicated_reach),
            "naive_reach_overstatement_pct": round(overstatement_pct, 1),
        })

    result_df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    result_df.to_csv(OUT_PATH, index=False)

    print(result_df.to_string(index=False))
    print(f"\nSaved to {OUT_PATH}")
    print(
        "\nTakeaway: reporting the naive summed reach number overstates "
        "true unique audience by roughly "
        f"{result_df['naive_reach_overstatement_pct'].min():.1f}% to "
        f"{result_df['naive_reach_overstatement_pct'].max():.1f}% depending on "
        "the true (unknown here, assumed) cross-platform overlap rate. "
        "That range is the actual point: cross-screen identity resolution "
        "is valuable precisely because without it, every multi-channel "
        "reach number is an assumption dressed up as a fact."
    )


if __name__ == "__main__":
    main()