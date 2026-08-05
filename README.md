# SponsorLift

**Cross-screen sponsorship exposure and ad-lift intelligence, built as a case study on a real 2026 sponsorship deal.**

Built for a Data Scientist, Broadcast interview, to demonstrate the three hardest measurement problems in sports sponsorship analytics: pricing exposure, proving causal ad impact, and deduplicating audiences across broadcast and social.

## Case study

Golden State Warriors × IREN Limited jersey patch, announced June 25, 2026, the richest jersey sponsorship deal in North American sports history (~$50M/year). Real, publicly documented event, used as the basis for every analysis below.

## What's real vs. simulated

This distinction is deliberate and disclosed everywhere it matters, not buried in a footnote, a measurement platform's numbers are only trustworthy if you know what's underneath them.

| Component | Status | Why |
|---|---|---|
| YouTube video engagement (views, likes, comments) | **Real** | Pulled live via the YouTube Data API v3 for the Warriors channel and three NBA control channels |
| Ad-lift regression | **Real analysis on real data** | Difference-in-differences on the engagement data above |
| Broadcast logo exposure events | **Simulated** | Zoomph's actual computer-vision detection output isn't publicly available. Simulated using documented, adjustable assumptions (appearance frequency, duration, clarity, centrality, clutter) rather than presented as real detection |
| CPM rate / average broadcast audience | **Illustrative placeholder** | Not a licensed ad-rate benchmark. Configurable constants, clearly labeled in source |
| Cross-screen audience overlap rate | **Assumed, swept across a range** | Real deduplication needs a cross-platform identity graph (device/login matching), which is exactly the kind of proprietary asset a company like Zoomph builds. Modeled here as a sensitivity range (10% / 25% / 45% overlap) instead of one invented precise number |

## Pipeline

src/ingest_youtube.py          → real YouTube engagement data (treatment + 3 control channels)
src/generate_exposure_events.py → simulated broadcast logo-appearance events
src/valuation_engine.py         → quality-weighted equivalent media value per broadcast
src/lift_model.py               → difference-in-differences ad-lift estimate, pooled + per-control robustness
src/dedup_model.py              → cross-screen reach, naive vs. deduplicated, swept across overlap assumptions
app/dashboard.py                → Streamlit report tying all of the above together

Data Flow:
YouTube API → YouTube Engagement Data
              ↓
        Control Channel Selection (Bulls, Nets, Nuggets)
              ↓
        Difference-in-Differences Regression (log scale, HC1 robust SEs)
              ↓
        Ad-Lift Estimate + Confidence Intervals
              ↓
Broadcast Schedule → Simulated Logo Exposure Events
                     (clarity, centrality, clutter, duration weighted)
                            ↓
                    CPM Rate Lookup
                            ↓
                    Equivalent Media Value ($711K)
                            ↓
        Cross-Screen Reach Model (broadcast + social, dedup overlap scenarios)
              ↓
        Streamlit Dashboard (KPIs, charts, methodology section)

Run in order:

```cmd
python src\ingest_youtube.py
python src\generate_exposure_events.py
python src\valuation_engine.py
python src\lift_model.py
python src\dedup_model.py
streamlit run app\dashboard.py
```

## Key results

- **Ad-lift (views, pooled across 3 controls):** -43.7% (95% CI: -73.3% to +18.8%), not statistically significant at n=1 event. Direction was consistent across all three control channels individually, which is reassuring, but a single-event sample can't support a confident causal claim, that limitation is the finding, not a bug in the analysis.
- **Simulated broadcast media value:** $711,626 across 12 simulated broadcasts, using placeholder CPM/audience assumptions that are trivially swappable for a real rate card.
- **Cross-screen reach overstatement:** naive summed reach overstates true unique audience by 2.4%–11.0% depending on the assumed overlap rate, which is the exact problem a cross-platform identity graph is built to solve.

## Why this approach

Zoomph's own materials describe their methodology as needing to be "explainable and defensible" even though the underlying models are proprietary. the inputs have to hold up to a skeptical client's finance team. This project is built to the same standard: every assumption is a named, adjustable constant in the source, not a black box, and the ad-lift result is reported with its actual uncertainty rather than rounded up into a clean story.

## What I'd do differently with more time / data

- More sponsorship events across more teams to get statistical power on the causal estimate
- Replace the exposure simulation with real detection output (would need licensed broadcast footage + a fine-tuned object detector, a realistic next phase, not an overnight one)
- Calibrate the CPM rate against real ad-rate data and the overlap rate against a real panel or identity-resolution source
- Add a time-series/event-study specification instead of a single pre/post window, to check the effect isn't concentrated in one anomalous week

## Stack

Python, pandas, NumPy, statsmodels (OLS with HC1 robust SEs), DuckDB-ready schema, Streamlit, Plotly, YouTube Data API v3.
