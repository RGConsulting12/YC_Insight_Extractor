# Script to scrape or load YouTube video URLs from YC channel or playlist

import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load API key from .env file
env_path = Path("/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/src/transcript/.env")
load_dotenv(dotenv_path=env_path)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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
            "key": GOOGLE_API_KEY
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

    # Load existing video IDs to merge (don't overwrite manually added videos)
    existing_video_ids = []
    video_ids_path = Path("data/video_ids.json")
    if video_ids_path.exists():
        try:
            with open(video_ids_path, "r") as f:
                existing_video_ids = json.load(f)
        except:
            existing_video_ids = []
    
    # Merge playlist videos with existing videos (avoid duplicates)
    all_video_ids = list(set(existing_video_ids + video_ids))
    
    # Save merged list to JSON file
    os.makedirs("data", exist_ok=True)
    with open("data/video_ids.json", "w") as f:
        json.dump(all_video_ids, f, indent=2)

    new_videos = len(all_video_ids) - len(existing_video_ids)
    print(f"✅ Saved {len(all_video_ids)} total video IDs to data/video_ids.json")
    if new_videos > 0:
        print(f"   Added {new_videos} new videos from playlist")
    else:
        print(f"   No new videos (all playlist videos already in list)")
