import os
import json
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

def get_transcript(video_id, save_dir="data/raw_transcripts"):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = "\n".join([entry["text"] for entry in transcript])
        os.makedirs(save_dir, exist_ok=True)
        with open(os.path.join(save_dir, f"{video_id}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ Saved transcript for {video_id}")
    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"⚠️ No transcript found for {video_id}")
    except Exception as e:
        print(f"❌ Error with {video_id}: {e}")

def batch_download_transcripts(video_ids):
    for vid in video_ids:
        get_transcript(vid)

if __name__ == "__main__":
    with open("data/video_ids.json", "r") as f:
        video_ids = json.load(f)

    print(f"📥 Downloading transcripts for {len(video_ids)} videos...\n")
    batch_download_transcripts(video_ids)
