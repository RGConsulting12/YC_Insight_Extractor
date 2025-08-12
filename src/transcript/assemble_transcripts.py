import os
import re
from collections import defaultdict

CHUNK_DIR = "data/chunk_transcripts"
MERGED_DIR = "data/raw_transcripts"
os.makedirs(MERGED_DIR, exist_ok=True)

def assemble_transcript(transcript_chunks):
    """
    Assemble a list of transcript chunks into a single transcript.
    
    Args:
        transcript_chunks (list): List of transcript text strings
    
    Returns:
        str: Assembled transcript
    """
    assembled = []
    
    for i, chunk in enumerate(transcript_chunks):
        if chunk.strip():  # Only add non-empty chunks
            assembled.append(f"\n\n=== chunk_{i} ===\n{chunk.strip()}")
    
    return "\n".join(assembled)

def extract_base_and_index(filename):
    match = re.match(r"(.+?)_(?:chapter|chunk)_(\d+)\.txt", filename)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

def group_chunks():
    grouped = defaultdict(list)
    # Traverse video ID subdirectories
    for video_id in os.listdir(CHUNK_DIR):
        video_dir = os.path.join(CHUNK_DIR, video_id)
        if os.path.isdir(video_dir):
            for filename in os.listdir(video_dir):
                if filename.endswith(".txt"):
                    base, idx = extract_base_and_index(filename)
                    if base is not None and idx is not None:
                        grouped[base].append((idx, filename))
    return grouped

def merge_chunks():
    grouped = group_chunks()

    for video_id, chunks in grouped.items():
        chunks.sort()  # sort by index
        merged_path = os.path.join(MERGED_DIR, f"{video_id}.txt")
        print(f"📦 Merging transcript for: {video_id}")

        with open(merged_path, "w", encoding="utf-8") as outfile:
            for idx, filename in chunks:
                # Fix: Include video_id subdirectory in path
                chunk_path = os.path.join(CHUNK_DIR, video_id, filename)
                with open(chunk_path, "r", encoding="utf-8") as infile:
                    text = infile.read().strip()
                    outfile.write(f"\n\n=== chunk_{idx} ===\n{text}")
        print(f"✅ Merged saved: {merged_path}")

if __name__ == "__main__":
    merge_chunks()
