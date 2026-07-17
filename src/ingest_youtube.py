r"""
Ingests real YouTube video-level engagement data for a treatment channel
(involved in a real sponsorship event) and multiple control channels (same
time window, no sponsorship event) so lift_model.py can run a
difference-in-differences estimate that nets out seasonal/trend effects,
and check that the result isn't an artifact of one arbitrarily chosen
control channel.

Run from the project root with the venv active:
    python src\ingest_youtube.py
"""

import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    sys.exit("YOUTUBE_API_KEY not found. Check your .env file exists and has the key set.")

youtube = build("youtube", "v3", developerKey=API_KEY)

# Real, documented sponsorship events. Add more here as you find them.
# control_channel_handles should be comparable channels with NO sponsorship
# change in the same window, used to net out seasonal/trend effects and
# check the result isn't an artifact of one control channel's own noise.
EVENTS = [
    {
        "event_name": "Warriors x IREN jersey patch",
        "sponsor": "IREN Limited",
        "treatment_channel_handle": "@warriors",
        "control_channel_handles": ["@chicagobulls", "@brooklynnets", "@denvernuggets"],
        "event_date": "2026-06-25",
        "pre_days": 21,
        "post_days": 21,
    },
]


def resolve_channel_id(handle):
    """Resolve a @handle to a channel ID and its uploads playlist ID."""
    handle_clean = handle.lstrip("@")
    resp = youtube.channels().list(
        part="contentDetails,snippet",
        forHandle=handle_clean,
    ).execute()

    items = resp.get("items", [])
    if not items:
        raise ValueError(
            f"No channel found for handle '{handle}'. "
            f"Open https://youtube.com/{handle} in a browser to confirm the exact handle, "
            f"then update EVENTS in this script."
        )

    channel = items[0]
    channel_id = channel["id"]
    uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    channel_title = channel["snippet"]["title"]
    return channel_id, uploads_playlist_id, channel_title


def fetch_uploads_in_window(playlist_id, start_date, end_date):
    """Page through a channel's uploads playlist, keep videos published in [start_date, end_date]."""
    video_ids = []
    published_map = {}
    page_token = None

    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()

        stop = False
        for item in resp.get("items", []):
            published_at = item["contentDetails"].get("videoPublishedAt")
            if not published_at:
                continue
            published_dt = datetime.strptime(published_at[:10], "%Y-%m-%d")

            if published_dt < start_date:
                stop = True
                continue
            if published_dt > end_date:
                continue

            video_id = item["contentDetails"]["videoId"]
            video_ids.append(video_id)
            published_map[video_id] = published_dt

        page_token = resp.get("nextPageToken")
        if not page_token or stop:
            break

    return video_ids, published_map


def fetch_video_stats(video_ids):
    """Batch-fetch statistics and titles for a list of video IDs, 50 at a time."""
    rows = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        resp = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(chunk),
        ).execute()

        for item in resp.get("items", []):
            stats = item.get("statistics", {})
            rows.append({
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            })
        time.sleep(0.2)  # stay well under quota rate limits

    return rows


def process_channel(group, handle, event, event_date, start_date, end_date):
    """Fetch and tag video rows for one channel. Returns a list of row dicts."""
    print(f"Processing event: {event['event_name']} [{group}: {handle}]")

    try:
        channel_id, uploads_playlist_id, channel_title = resolve_channel_id(handle)
    except ValueError as e:
        print(f"  SKIPPED: {e}")
        return []
    except HttpError as e:
        print(f"  API ERROR resolving channel: {e}")
        return []

    video_ids, published_map = fetch_uploads_in_window(uploads_playlist_id, start_date, end_date)
    print(f"  Found {len(video_ids)} videos in window {start_date.date()} to {end_date.date()}")

    if not video_ids:
        print("  No videos found in this window, skipping.")
        return []

    stats_rows = fetch_video_stats(video_ids)
    rows = []
    for row in stats_rows:
        published_dt = published_map[row["video_id"]]
        row["event_name"] = event["event_name"]
        row["sponsor"] = event["sponsor"]
        row["group"] = group
        row["control_channel"] = handle if group == "control" else None
        row["channel_title"] = channel_title
        row["published_at"] = published_dt.strftime("%Y-%m-%d")
        row["days_from_event"] = (published_dt - event_date).days
        row["is_post_event"] = published_dt >= event_date
        rows.append(row)

    return rows


def main():
    all_rows = []

    for event in EVENTS:
        event_date = datetime.strptime(event["event_date"], "%Y-%m-%d")
        start_date = event_date - timedelta(days=event["pre_days"])
        end_date = event_date + timedelta(days=event["post_days"])

        all_rows.extend(
            process_channel("treatment", event["treatment_channel_handle"], event, event_date, start_date, end_date)
        )

        for control_handle in event["control_channel_handles"]:
            all_rows.extend(
                process_channel("control", control_handle, event, event_date, start_date, end_date)
            )

    if not all_rows:
        sys.exit("No data collected across any event. Check channel handles and dates in EVENTS.")

    df = pd.DataFrame(all_rows)
    out_path = os.path.join("data", "raw", "youtube_video_stats.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved {len(df)} rows to {out_path}")
    print(df.groupby(["group", "control_channel", "is_post_event"], dropna=False)[["view_count", "like_count", "comment_count"]].mean())


if __name__ == "__main__":
    main()