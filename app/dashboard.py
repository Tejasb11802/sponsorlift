r"""
SponsorLift dashboard: presents the broadcast valuation, ad-lift causal
estimate, and cross-screen reach deduplication results as a single
report, in the style of a sponsorship intelligence deliverable.

Run from the project root with the venv active:
    streamlit run app\dashboard.py
"""

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

VALUATION_PATH = os.path.join("data", "processed", "broadcast_valuation.csv")
LIFT_PATH = os.path.join("data", "processed", "lift_estimates.csv")
DEDUP_PATH = os.path.join("data", "processed", "cross_screen_reach.csv")

# ---------------------------------------------------------------------
# Page config and theme
# ---------------------------------------------------------------------
st.set_page_config(page_title="SponsorLift", page_icon="\U0001F4E1", layout="wide")

BG = "#0E1420"
CARD = "#161D2E"
BORDER = "#232B3D"
TEXT = "#E8EAF0"
MUTED = "#8993A8"
GOLD = "#D4A24E"
TEAL = "#4FAF8C"
RED = "#E2574C"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    .stApp {{
        background-color: {BG};
        color: {TEXT};
    }}
    section[data-testid="stSidebar"] {{
        background-color: {CARD};
    }}
    h1, h2, h3 {{
        font-family: 'Space Grotesk', sans-serif !important;
        color: {TEXT} !important;
    }}
    .eyebrow {{
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {GOLD};
        font-size: 0.8rem;
        margin-bottom: 0.25rem;
    }}
    .subtitle {{
        color: {MUTED};
        font-size: 0.95rem;
        margin-top: -0.5rem;
    }}
    .kpi-card {{
        background-color: {CARD};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 1.1rem 1.3rem;
    }}
    .kpi-label {{
        font-family: 'IBM Plex Mono', monospace;
        color: {MUTED};
        font-size: 0.78rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}
    .kpi-value {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.9rem;
        font-weight: 700;
        margin-top: 0.15rem;
    }}
    .kpi-note {{
        color: {MUTED};
        font-size: 0.8rem;
        margin-top: 0.15rem;
    }}
    .section-divider {{
        border-top: 1px solid {BORDER};
        margin: 2rem 0 1.2rem 0;
    }}
    .assumption-box {{
        background-color: {CARD};
        border: 1px solid {BORDER};
        border-left: 3px solid {GOLD};
        border-radius: 4px;
        padding: 1rem 1.2rem;
        font-size: 0.88rem;
        color: {MUTED};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

PLOTLY_LAYOUT = dict(
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    font=dict(family="IBM Plex Mono, monospace", color=TEXT, size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
)


# ---------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------
def load_data():
    missing = [p for p in [VALUATION_PATH, LIFT_PATH, DEDUP_PATH] if not os.path.exists(p)]
    if missing:
        st.error(
            "Missing pipeline output(s):\n\n"
            + "\n".join(f"- `{p}`" for p in missing)
            + "\n\nRun, in order: `ingest_youtube.py`, `generate_exposure_events.py`, "
              "`valuation_engine.py`, `lift_model.py`, `dedup_model.py`."
        )
        st.stop()

    valuation_df = pd.read_csv(VALUATION_PATH)
    lift_df = pd.read_csv(LIFT_PATH)
    dedup_df = pd.read_csv(DEDUP_PATH)
    return valuation_df, lift_df, dedup_df


def kpi_card(col, label, value, note, color=None):
    color = color or "inherit"
    col.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color}">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------
def render_header():
    st.markdown('<div class="eyebrow">Sponsorship Broadcast Intelligence &middot; Case Study</div>', unsafe_allow_html=True)
    st.markdown("## SponsorLift")
    st.markdown(
        '<div class="subtitle">Golden State Warriors &times; IREN Limited jersey patch, announced June 25, 2026. '
        "Broadcast exposure is a documented simulation (see Methodology below); the ad-lift estimate runs on real "
        "YouTube engagement data.</div>",
        unsafe_allow_html=True,
    )


def render_kpis(valuation_df, lift_df, dedup_df):
    total_value = valuation_df["equivalent_media_value_usd"].sum()
    n_broadcasts = valuation_df["broadcast_id"].nunique()

    pooled_view = lift_df[(lift_df["control_set"] == "pooled (all controls)") & (lift_df["metric"] == "view_count")].iloc[0]
    lift_val = pooled_view["pct_lift"]
    lift_sig = bool(pooled_view["significant_at_5pct"])
    lift_color = TEAL if lift_val >= 0 else RED

    mid_scenario = dedup_df[dedup_df["scenario"] == "mid_overlap"].iloc[0]
    overstatement = mid_scenario["naive_reach_overstatement_pct"]

    cols = st.columns(4)
    kpi_card(
        cols[0],
        "Simulated broadcast value",
        f"${total_value:,.0f}",
        f"across {n_broadcasts} broadcasts (illustrative CPM assumption)",
        color=GOLD,
    )
    kpi_card(
        cols[1],
        "Ad-lift estimate (views)",
        f"{lift_val:+.1f}%",
        "significant at p<0.05" if lift_sig else "not statistically significant (n=1 event)",
        color=lift_color,
    )
    kpi_card(
        cols[2],
        "Reach overstatement (mid case)",
        f"{overstatement:.1f}%",
        "naive summed reach vs. deduplicated estimate",
        color=GOLD,
    )
    kpi_card(
        cols[3],
        "Videos analyzed",
        f"{int(lift_df[lift_df['control_set'] == 'pooled (all controls)']['n_obs'].iloc[0])}",
        "real YouTube data, treatment + control channels",
        color=TEXT,
    )


def render_valuation(valuation_df):
    st.markdown("### Broadcast Exposure & Valuation")
    st.caption(
        "Simulated logo-appearance events, weighted by clarity, centrality, and clutter before pricing. "
        "See Methodology for the exact formula and its assumptions."
    )
    fig = go.Figure()
    fig.add_bar(
        x=valuation_df["broadcast_id"],
        y=valuation_df["equivalent_media_value_usd"],
        marker_color=GOLD,
        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=340, yaxis_title="Equivalent media value (USD)")
    st.plotly_chart(fig, width="stretch")


def render_lift(lift_df):
    st.markdown("### Ad-Lift Causal Analysis")
    st.caption(
        "Difference-in-differences, log scale. Pooled estimate (gold) vs. the same model re-run against each "
        "control channel individually (grey), to check the result isn't an artifact of one control's own noise."
    )

    metric = st.selectbox("Metric", ["view_count", "like_count", "comment_count"], index=0)
    sub = lift_df[lift_df["metric"] == metric].copy()
    sub["is_pooled"] = sub["control_set"] == "pooled (all controls)"
    sub = sub.sort_values("is_pooled")

    fig = go.Figure()
    for _, row in sub.iterrows():
        color = GOLD if row["is_pooled"] else MUTED
        fig.add_trace(
            go.Scatter(
                x=[row["pct_lift"]],
                y=[row["control_set"]],
                mode="markers",
                marker=dict(color=color, size=14 if row["is_pooled"] else 10),
                error_x=dict(
                    type="data",
                    symmetric=False,
                    array=[row["pct_lift_ci_high"] - row["pct_lift"]],
                    arrayminus=[row["pct_lift"] - row["pct_lift_ci_low"]],
                    color=color,
                ),
                showlegend=False,
                hovertemplate=f"{row['control_set']}<br>%{{x:.1f}}% (p={row['p_value']:.3f})<extra></extra>",
            )
        )
    fig.add_vline(x=0, line_dash="dash", line_color=BORDER)
    fig.update_layout(**PLOTLY_LAYOUT, height=280, xaxis_title="Estimated % lift (95% CI)")
    st.plotly_chart(fig, width="stretch")


def render_dedup(dedup_df):
    st.markdown("### Cross-Screen Reach Deduplication")
    st.caption(
        "Naive summed reach (broadcast + social) vs. a deduplicated estimate, swept across a range of assumed "
        "cross-platform audience overlap since the real overlap rate requires an identity graph this project "
        "doesn't have access to."
    )

    fig = go.Figure()
    fig.add_bar(
        name="Naive summed reach",
        x=dedup_df["scenario"],
        y=dedup_df["naive_summed_reach"],
        marker_color=RED,
    )
    fig.add_bar(
        name="Deduplicated reach",
        x=dedup_df["scenario"],
        y=dedup_df["deduplicated_unique_reach"],
        marker_color=TEAL,
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=320, barmode="group", yaxis_title="Estimated reach")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(dedup_df, width="stretch", hide_index=True)


def render_methodology():
    st.markdown("### Methodology & Assumptions")
    st.markdown(
        f"""
        <div class="assumption-box">
        <b>What's real:</b> YouTube video-level engagement (views, likes, comments) for the Warriors channel and
        three NBA control channels, pulled via the YouTube Data API. The ad-lift regression runs on this real data.<br><br>
        <b>What's simulated:</b> broadcast-level logo exposure events (Zoomph's real computer-vision detection output
        isn't publicly available), the CPM rate and average audience used to price that exposure, and the
        cross-screen audience overlap rate. Each is a labeled, adjustable parameter in the source, not a hidden
        constant.<br><br>
        <b>Why this matters:</b> a measurement platform's numbers are only as trustworthy as its disclosed
        assumptions. This project treats "what's real vs. assumed" as a first-class thing to show, not a caveat
        to bury in a footnote.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    valuation_df, lift_df, dedup_df = load_data()

    render_header()
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    render_kpis(valuation_df, lift_df, dedup_df)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    render_valuation(valuation_df)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    render_lift(lift_df)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    render_dedup(dedup_df)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    render_methodology()


if __name__ == "__main__":
    main()