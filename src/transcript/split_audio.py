import os
import re
import json
import subprocess
from pathlib import Path

# Updated to use more flexible paths
def get_project_paths():
    """Get project paths relative to this file"""
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    return {
        "audio_dir": project_root / "src" / "transcript" / "data" / "audio",
        "metadata_dir": project_root / "src" / "scraper" / "data" / "metadata",
        "chunks_dir": project_root / "src" / "transcript" / "data" / "audio_chunks"
    }

# Legacy paths for backward compatibility
AUDIO_DIR = "data/audio"
METADATA_DIR = "data/metadata"
CHUNKS_DIR = "data/audio_chunks"


def parse_chapters_from_description(description):
    pattern = re.compile(r'(?P<time>\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—]?\s*(?P<title>.+)')
    chapters = []

    for line in description.splitlines():
        match = pattern.match(line.strip())
        if match:
            time_str = match.group("time")
            title = match.group("title").strip()
            time_parts = [int(part) for part in time_str.split(":")]
            if len(time_parts) == 2:
                seconds = time_parts[0] * 60 + time_parts[1]
            elif len(time_parts) == 3:
                seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
            else:
                continue
            chapters.append({"start": seconds, "title": title})

    return chapters


def get_chapters(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Attempt to get structured chapters via yt-dlp
    try:
        result = subprocess.run([
            "yt-dlp",
            "--print", "%(chapters_json)s",
            video_url
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        output = result.stdout.strip()
        if output and output != "None":
            return json.loads(output)
    except Exception as e:
        print(f"⚠️ yt-dlp error for {video_id}: {e}")

    # Fallback: try to parse chapters from video description
    metadata_path = os.path.join(METADATA_DIR, f"{video_id}.json")
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)
            description = metadata.get("snippet", {}).get("description", "")
            raw_chapters = parse_chapters_from_description(description)

            # Turn into chapter JSON format with end times
            chapters = []
            for i, chap in enumerate(raw_chapters):
                chapters.append({
                    "start_time": chap["start"],
                    "end_time": raw_chapters[i + 1]["start"] if i + 1 < len(raw_chapters) else None,
                    "title": chap["title"]
                })
            return chapters if chapters else None
    return None


def split_by_chapters(audio_path, chapters, base_name, output_dir):
    chunk_files = []
    duration_cmd = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    total_duration = float(duration_cmd.stdout.strip())

    for i, chapter in enumerate(chapters):
        start = chapter.get("start_time")
        end = chapter.get("end_time") or total_duration
        title = chapter.get("title", f"chapter_{i}")
        slug = title.lower().replace(" ", "_").replace(":", "").replace("-", "").replace("—", "")
        output_path = os.path.join(output_dir, f"{base_name}_chapter_{i}_{slug}.mp3")

        subprocess.run([
            "ffmpeg", "-i", audio_path,
            "-ss", str(start), "-to", str(end),
            "-c", "copy", output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        chunk_files.append(output_path)
    return chunk_files


def split_by_length(audio_path, base_name, output_dir, chunk_duration=1200, overlap=200):
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    duration = float(result.stdout.strip())
    chunk_files = []
    start = 0
    i = 0

    while start < duration:
        end = min(start + chunk_duration, duration)
        output_path = os.path.join(output_dir, f"{base_name}_chunk_{i}.mp3")

        subprocess.run([
            "ffmpeg", "-i", audio_path,
            "-ss", str(start), "-to", str(end),
            "-c", "copy", output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        chunk_files.append(output_path)
        start += chunk_duration - overlap
        i += 1

    return chunk_files


def process_audio_file(audio_file):
    video_id = os.path.splitext(os.path.basename(audio_file))[0]

    print(f"\n🔍 Processing {video_id}...")
    chapters = get_chapters(video_id)

    if chapters:
        print("📘 Chapters found. Splitting by chapters.")
        return split_by_chapters(audio_file, chapters, video_id)
    else:
        print("⚠️ No chapters found. Splitting by fixed length.")
        return split_by_length(audio_file, video_id)


def split_audio_file(audio_path, output_dir=None):
    """
    Split an audio file into chunks.
    
    Args:
        audio_path (str): Path to the audio file
        output_dir (str): Directory to save chunks (optional)
    
    Returns:
        list: List of paths to chunk files
    """
    audio_path = Path(audio_path)
    video_id = audio_path.stem
    
    if output_dir is None:
        # Use the legacy chunks directory structure
        output_dir = Path(CHUNKS_DIR) / video_id
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔍 Processing {video_id}...")
    chapters = get_chapters(video_id)

    if chapters:
        print("📘 Chapters found. Splitting by chapters.")
        return split_by_chapters(str(audio_path), chapters, video_id, str(output_dir))
    else:
        print("⚠️ No chapters found. Splitting by fixed length.")
        return split_by_length(str(audio_path), video_id, str(output_dir))


if __name__ == "__main__":
    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")]

    for file in audio_files:
        full_path = os.path.join(AUDIO_DIR, file)
        chunk_paths = process_audio_file(full_path)
        print(f"✅ Created {len(chunk_paths)} chunks for {file}")
