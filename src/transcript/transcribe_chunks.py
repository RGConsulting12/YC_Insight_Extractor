import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Load OpenAI API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define directories
CHUNKS_DIR = "data/audio_chunks"
TRANSCRIPTS_DIR = "data/chunk_transcripts"
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

def transcribe_chunk(chunk_path):
    """Send audio file to OpenAI Whisper for transcription"""
    with open(chunk_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=f
        )
    return response.text

def transcribe_audio_chunks(chunk_files):
    """
    Transcribe a list of audio chunk files.
    
    Args:
        chunk_files (list): List of paths to audio chunk files
    
    Returns:
        list: List of transcript texts in order
    """
    transcripts = []
    
    for chunk_path in chunk_files:
        print(f"📝 Transcribing: {Path(chunk_path).name}")
        try:
            transcript = transcribe_chunk(chunk_path)
            transcripts.append(transcript)
            print(f"✅ Transcribed: {Path(chunk_path).name}")
        except Exception as e:
            print(f"❌ Failed to transcribe {chunk_path}: {e}")
            # Add empty transcript to maintain order
            transcripts.append("")
    
    return transcripts

def process_all_chunks():
    """Loop through audio chunks and transcribe each"""
    chunk_files = [f for f in os.listdir(CHUNKS_DIR) if f.endswith(".mp3")]

    for chunk_file in chunk_files:
        chunk_path = os.path.join(CHUNKS_DIR, chunk_file)

        # Extract video ID to organize transcripts
        video_id = chunk_file.split("_")[0]
        video_transcript_dir = os.path.join(TRANSCRIPTS_DIR, video_id)
        os.makedirs(video_transcript_dir, exist_ok=True)

        # Create transcript path
        transcript_file = chunk_file.replace(".mp3", ".txt")
        transcript_path = os.path.join(video_transcript_dir, transcript_file)

        if os.path.exists(transcript_path):
            print(f"⏩ Already transcribed: {chunk_file}")
            continue

        print(f"📝 Transcribing: {chunk_file}")
        try:
            transcript = transcribe_chunk(chunk_path)
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)
            print(f"✅ Saved: {transcript_path}")
        except Exception as e:
            print(f"❌ Failed: {chunk_file} – {e}")
            with open("transcription_errors.log", "a") as log:
                log.write(f"{chunk_file}: {e}\n")

if __name__ == "__main__":
    process_all_chunks()
