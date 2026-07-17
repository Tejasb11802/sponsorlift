r"""
Difference-in-differences estimate of sponsorship ad-lift, using
statsmodels OLS with heteroskedasticity-robust (HC1) standard errors.

Model: log(1 + metric) ~ treatment + post + treatment:post
The coefficient on the treatment:post interaction is the DiD estimate,
on a log scale. exp(coef) - 1 converts it to a percentage lift.

Log scale is used because engagement counts are right-skewed and roughly
multiplicative across channels of very different subscriber sizes, so a
level-difference DiD (like a raw mean subtraction) is misleading here.

Two results are produced:
  1. POOLED: all control channels combined into one "control" group.
     This is the headline estimate.
  2. PER-CONTROL ROBUSTNESS: the same DiD re-run against each control
     channel individually. If the pooled estimate only holds up for one
     specific control channel, that's a red flag the result is driven by
     that channel's own noise rather than a real effect.

Run from the project root with the venv active:
    python src\lift_model.py
"""

import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

IN_PATH = os.path.join("data", "raw", "youtube_video_stats.csv")
OUT_PATH = os.path.join("data", "processed", "lift_estimates.csv")

METRICS = ["view_count", "like_count", "comment_count"]


def run_did(data, metric):
    """Fit one DiD regression for a single metric on the given subset. Returns a result dict."""
    data = data.copy()
    data["treatment"] = (data["group"] == "treatment").astype(int)
    data["post"] = data["is_post_event"].astype(int)
    data["log_metric"] = np.log1p(data[metric])

    model = smf.ols("log_metric ~ treatment * post", data=data)
    fit = model.fit(cov_type="HC1")

    coef = fit.params["treatment:post"]
    se = fit.bse["treatment:post"]
    p_value = fit.pvalues["treatment:post"]
    ci_low, ci_high = fit.conf_int().loc["treatment:post"]

    pct_lift = (np.exp(coef) - 1) * 100
    pct_lift_low = (np.exp(ci_low) - 1) * 100
    pct_lift_high = (np.exp(ci_high) - 1) * 100

    return {
        "metric": metric,
        "n_obs": int(fit.nobs),
        "did_coefficient": round(coef, 4),
        "std_error": round(se, 4),
        "p_value": round(p_value, 4),
        "significant_at_5pct": bool(p_value < 0.05),
        "pct_lift": round(pct_lift, 1),
        "pct_lift_ci_low": round(pct_lift_low, 1),
        "pct_lift_ci_high": round(pct_lift_high, 1),
    }


def main():
    if not os.path.exists(IN_PATH):
        raise SystemExit(f"{IN_PATH} not found. Run src\\ingest_youtube.py first.")

    df = pd.read_csv(IN_PATH)

    required_cols = {"group", "is_post_event"} | set(METRICS)
    missing = required_cols - set(df.columns)
    if missing:
        raise SystemExit(f"Missing expected columns in input data: {missing}")

    # --- Pooled estimate: all controls combined ---
    pooled_results = [run_did(df, metric) for metric in METRICS]
    pooled_df = pd.DataFrame(pooled_results)
    pooled_df.insert(0, "control_set", "pooled (all controls)")

    # --- Per-control robustness check ---
    control_channels = sorted(df.loc[df["group"] == "control", "control_channel"].dropna().unique())
    robustness_rows = []
    for control_channel in control_channels:
        subset = df[(df["group"] == "treatment") | (df["control_channel"] == control_channel)]
        for metric in METRICS:
            result = run_did(subset, metric)
            result_row = {"control_set": control_channel, **result}
            robustness_rows.append(result_row)
    robustness_df = pd.DataFrame(robustness_rows)

    combined = pd.concat([pooled_df, robustness_df], ignore_index=True)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    combined.to_csv(OUT_PATH, index=False)

    print(f"\n=== POOLED DiD estimate (n={len(df)} videos total) ===\n")
    print(pooled_df.drop(columns="control_set").to_string(index=False))

    print(f"\n=== Per-control robustness check ({len(control_channels)} control channels) ===\n")
    for metric in METRICS:
        sub = robustness_df[robustness_df["metric"] == metric]
        print(f"\n{metric}:")
        print(sub[["control_set", "pct_lift", "pct_lift_ci_low", "pct_lift_ci_high", "p_value", "significant_at_5pct"]].to_string(index=False))

    print(f"\nSaved full results to {OUT_PATH}")

    print("\nInterpretation notes:")
    for r in pooled_results:
        sig = "statistically significant" if r["significant_at_5pct"] else "NOT statistically significant"
        direction = "lift" if r["pct_lift"] >= 0 else "decline"
        print(
            f"  {r['metric']}: pooled estimate {abs(r['pct_lift'])}% {direction} "
            f"(95% CI: {r['pct_lift_ci_low']}% to {r['pct_lift_ci_high']}%), {sig} at p={r['p_value']}"
        )
    print(
        "\n  Check the per-control robustness table above: if the sign and rough "
        "magnitude hold across all three control channels, the pooled estimate is "
        "reasonably trustworthy. If one control channel gives a wildly different "
        "answer than the others, that channel likely had its own idiosyncratic "
        "shock in this window and the pooled number is being skewed by it."
    )


if __name__ == "__main__":
    main()