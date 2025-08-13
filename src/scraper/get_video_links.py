# Script to scrape or load YouTube video URLs from YC channel or playlist

import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load API key from .env file
env_path = Path("/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/src/transcript/.env")
load_dotenv(dotenv_path=env_path)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Constants
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
PLAYLIST_ID = "PLQ-uHSnFig5NPx4adxl97CZb8vU4numwi"  # ← Replace with any YC playlist ID
MAX_RESULTS = 50  # Max allowed per API call

def get_videos_from_playlist(playlist_id):
    videos = []
    next_page_token = None

    while True:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": MAX_RESULTS,
            "pageToken": next_page_token,
            "key": YOUTUBE_API_KEY
        }

        response = requests.get(f"{YOUTUBE_API_URL}/playlistItems", params=params)
        data = response.json()

        for item in data.get("items", []):
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            videos.append(video_id)

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return videos

if __name__ == "__main__":
    video_ids = get_videos_from_playlist(PLAYLIST_ID)

    # Save to JSON file
    os.makedirs("data", exist_ok=True)
    with open("data/video_ids.json", "w") as f:
        json.dump(video_ids, f, indent=2)

    print(f"✅ Saved {len(video_ids)} video IDs to data/video_ids.json")
