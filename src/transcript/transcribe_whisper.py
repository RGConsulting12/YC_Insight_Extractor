import os
import subprocess
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

AUDIO_DIR = "data/audio"
CHUNKS_DIR = "data/audio_chunks"
TRANSCRIPT_DIR = "data/raw_transcripts"

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(CHUNKS_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

def download_audio(video_url, out_path):
    result = subprocess.run([
        "yt-dlp",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "mp3",
        "--output", out_path,
        video_url
    ])
    return result.returncode == 0

def get_chapters(video_url):
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
        print(f"⚠️ Error retrieving chapters: {e}")
    return None

def split_audio_by_chapters(audio_path, chapters, base_name):
    chunk_files = []
    for i, chapter in enumerate(chapters):
        start = chapter.get('start_time')
        end = chapter.get('end_time')
        title = chapter.get('title', f"chapter_{i}")
        output_file = os.path.join(CHUNKS_DIR, f"{base_name}_chapter_{i}.mp3")

        subprocess.run([
            "ffmpeg",
            "-i", audio_path,
            "-ss", str(start),
            "-to", str(end),
            "-c", "copy",
            output_file,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        chunk_files.append((output_file, title))
    return chunk_files

def split_audio_by_length(audio_path, base_name, chunk_duration=1200, overlap=200):
    result = subprocess.run([
        "ffprobe",
        "-v", "error",
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
        output_file = os.path.join(CHUNKS_DIR, f"{base_name}_chunk_{i}.mp3")
        subprocess.run([
            "ffmpeg",
            "-i", audio_path,
            "-ss", str(start),
            "-to", str(end),
            "-c", "copy",
            output_file,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        chunk_files.append((output_file, f"chunk_{i}"))
        start += chunk_duration - overlap
        i += 1
    return chunk_files

def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcript = client_openai.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=f
        )
    return transcript.text

def process_video(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    audio_file = os.path.join(AUDIO_DIR, f"{video_id}.mp3")
    transcript_file = os.path.join(TRANSCRIPT_DIR, f"{video_id}.txt")

    print(f"\n🔊 Downloading audio for {video_id}...")
    if not download_audio(video_url, audio_file):
        print(f"❌ Failed to download audio for {video_id}")
        return

    print("🔍 Checking for chapters...")
    chapters = get_chapters(video_url)

    if chapters:
        print("📘 Chapters found. Splitting by chapters.")
        chunks = split_audio_by_chapters(audio_file, chapters, video_id)
    else:
        print("⚠️ No chapters found. Splitting by fixed length.")
        chunks = split_audio_by_length(audio_file, video_id)

    with open(transcript_file, "w", encoding="utf-8") as f:
        for path, label in chunks:
            print(f"📝 Transcribing: {label}")
            try:
                text = transcribe_audio(path)
                f.write(f"\n\n=== {label} ===\n{text}")
            except Exception as e:
                print(f"❌ Error transcribing {label}: {e}")

    print(f"✅ Transcript saved: {transcript_file}")

if __name__ == "__main__":
    with open("data/video_ids.json") as f:
        video_ids = json.load(f)

    for vid in video_ids[:13]:  # test on 3
        process_video(vid)
