import os
import json
import subprocess
import sys
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
VIDEO_IDS_PATH = PROJECT_ROOT / "src" / "scraper" / "data" / "video_ids.json"
AUDIO_DIR = PROJECT_ROOT / "src" / "transcript" / "data" / "audio"

# Create audio directory if it doesn't exist
os.makedirs(AUDIO_DIR, exist_ok=True)

def check_yt_dlp():
    """Check if yt-dlp is installed and available"""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def download_audio(video_id, retry_count=0):
    """Download audio from YouTube video"""
    output_path = AUDIO_DIR / f"{video_id}.mp3"
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Check if already downloaded
    if output_path.exists():
        print(f"✅ Already downloaded: {video_id}")
        return True

    print(f"🔊 Downloading: {video_id} ({retry_count + 1}/3)")
    
    try:
        # Use yt-dlp with better options for audio extraction
        result = subprocess.run([
            "yt-dlp",
            "-x",  # extract audio
            "--audio-format", "mp3",
            "--audio-quality", "0",  # best quality
            "--no-playlist",  # don't download playlists
            "--no-warnings",  # reduce noise
            "--extract-audio",  # ensure audio extraction
            "-o", str(output_path),
            video_url
        ], capture_output=True, text=True, check=True)
        
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"✅ Successfully downloaded: {video_id}")
            return True
        else:
            print(f"⚠️  Download completed but file is empty: {video_id}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to download {video_id}: {e}")
        if retry_count < 2:
            print(f"🔄 Retrying... ({retry_count + 1}/3)")
            return download_audio(video_id, retry_count + 1)
        return False
    except Exception as e:
        print(f"❌ Unexpected error downloading {video_id}: {e}")
        return False

def main():
    """Main function to download all videos"""
    # Check if yt-dlp is available
    if not check_yt_dlp():
        print("❌ yt-dlp is not installed or not available in PATH")
        print("Please install it with: pip install yt-dlp")
        sys.exit(1)
    
    # Check if video IDs file exists
    if not VIDEO_IDS_PATH.exists():
        print(f"❌ Video IDs file not found: {VIDEO_IDS_PATH}")
        sys.exit(1)
    
    # Load video IDs
    try:
        with open(VIDEO_IDS_PATH, 'r') as f:
            video_ids = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error reading video IDs file: {e}")
        sys.exit(1)
    
    print(f"📋 Found {len(video_ids)} videos to download")
    print(f"📁 Audio will be saved to: {AUDIO_DIR}")
    print("-" * 50)
    
    # Download each video
    successful = 0
    failed = 0
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] ", end="")
        if download_audio(video_id):
            successful += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"📊 Download Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📁 Audio files saved to: {AUDIO_DIR}")

if __name__ == "__main__":
    main()
