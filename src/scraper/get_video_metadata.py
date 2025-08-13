import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# === Load API key from .env ===
env_path = Path("/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/src/transcript/.env")
load_dotenv(dotenv_path=env_path)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
assert YOUTUBE_API_KEY, "❌ YOUTUBE_API_KEY not found in .env"

# === Paths ===
VIDEO_IDS_PATH = "data/video_ids.json"
METADATA_DIR = "data/metadata"
ALL_METADATA_PATH = os.path.join(METADATA_DIR, "all_metadata.json")
os.makedirs(METADATA_DIR, exist_ok=True)

# === Fetch metadata for a single video ===
def fetch_video_metadata(video_id):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,contentDetails,statistics,status",
        "id": video_id,
        "key": YOUTUBE_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        
        # Handle different response codes (following API docs)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items")
            if items:
                return items[0]
            else:
                print(f"⚠️ No metadata found for {video_id}")
                return None
        elif response.status_code == 403:
            error_data = response.json()
            if "quotaExceeded" in error_data.get("error", {}).get("errors", [{}])[0].get("reason", ""):
                print("❌ YouTube API quota exceeded")
            elif "keyInvalid" in error_data.get("error", {}).get("errors", [{}])[0].get("reason", ""):
                print("❌ Invalid YouTube API key")
            else:
                print(f"❌ YouTube API access denied: {error_data}")
            return None
        elif response.status_code == 400:
            print(f"❌ Bad request for {video_id}: {response.text}")
            return None
        else:
            print(f"❌ YouTube API error {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        return None

# === Main ===
def main():
    with open(VIDEO_IDS_PATH) as f:
        video_ids = json.load(f)

    all_metadata = []

    for vid in video_ids:
        print(f"\n📥 Fetching metadata for {vid}")
        metadata = fetch_video_metadata(vid)
        if metadata:
            title = metadata.get("snippet", {}).get("title", "Unknown Title")
            print(f"🎬 Title: {title}")

            with open(os.path.join(METADATA_DIR, f"{vid}.json"), "w", encoding="utf-8") as f_out:
                json.dump(metadata, f_out, indent=2, ensure_ascii=False)

            all_metadata.append(metadata)
            print(f"✅ Saved metadata: {vid}.json")
        else:
            print(f"❌ Skipped saving for {vid}")

        time.sleep(0.2)  # polite delay for rate limits

    # Save all metadata in one file
    with open(ALL_METADATA_PATH, "w", encoding="utf-8") as f_all:
        json.dump(all_metadata, f_all, indent=2, ensure_ascii=False)
    print(f"\n📦 Saved all metadata to: {ALL_METADATA_PATH}")

if __name__ == "__main__":
    main()
