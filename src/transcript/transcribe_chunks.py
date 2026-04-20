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
    # #region agent log
    try:
        import json as json_module
        import time as time_module
        import os as os_module
        chunk_stat = os_module.stat(chunk_path) if os_module.path.exists(chunk_path) else None
        with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
            f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"T1","location":"transcribe_chunks.py:15","message":"transcribe_chunk() called","data":{"chunk_path":str(chunk_path),"file_exists":os_module.path.exists(chunk_path),"file_size":chunk_stat.st_size if chunk_stat else None,"api_key_set":bool(os_module.getenv("OPENAI_API_KEY"))},"timestamp":int(time_module.time()*1000)}) + '\n')
    except:
        pass
    # #endregion
    try:
        with open(chunk_path, "rb") as f:
            # #region agent log
            try:
                import json as json_module
                import time as time_module
                with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f_log:
                    f_log.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"T2","location":"transcribe_chunks.py:22","message":"About to call OpenAI API","data":{"chunk_path":str(chunk_path),"model":"gpt-4o-transcribe"},"timestamp":int(time_module.time()*1000)}) + '\n')
            except:
                pass
            # #endregion
            response = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",  # ← OpenAI's Whisper API
                file=f
            )
            # #region agent log
            try:
                import json as json_module
                import time as time_module
                with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f_log:
                    f_log.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"T2","location":"transcribe_chunks.py:30","message":"OpenAI API call succeeded","data":{"chunk_path":str(chunk_path),"transcript_length":len(response.text) if response else 0},"timestamp":int(time_module.time()*1000)}) + '\n')
            except:
                pass
            # #endregion
            return response.text
    except Exception as e:
        # #region agent log
        try:
            import json as json_module
            import time as time_module
            import traceback as tb_module
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f_log:
                f_log.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"T3","location":"transcribe_chunks.py:35","message":"transcribe_chunk() exception","data":{"chunk_path":str(chunk_path),"error_type":type(e).__name__,"error_message":str(e),"traceback":tb_module.format_exc()},"timestamp":int(time_module.time()*1000)}) + '\n')
        except:
            pass
        # #endregion
        raise

def transcribe_audio_chunks(chunk_files, progress_callback=None):
    """
    Transcribe a list of audio chunk files.
    
    Args:
        chunk_files (list): List of paths to audio chunk files
        progress_callback (callable): Optional callback function(current_chunk, total_chunks)
    
    Returns:
        list: List of transcript texts in order
    """
    transcripts = []
    total_chunks = len(chunk_files)
    
    for i, chunk_path in enumerate(chunk_files, 1):
        # #region agent log
        try:
            import json as json_module
            import time as time_module
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"T4","location":"transcribe_chunks.py:38","message":"Starting transcription of chunk","data":{"chunk_index":i,"total_chunks":total_chunks,"chunk_path":str(chunk_path)},"timestamp":int(time_module.time()*1000)}) + '\n')
        except:
            pass
        # #endregion
        print(f"📝 Transcribing: {Path(chunk_path).name}")
        if progress_callback:
            progress_callback(i, total_chunks)
        try:
            transcript = transcribe_chunk(chunk_path)
            transcripts.append(transcript)
            # #region agent log
            try:
                import json as json_module
                import time as time_module
                with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                    f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"T4","location":"transcribe_chunks.py:50","message":"Chunk transcription succeeded","data":{"chunk_index":i,"chunk_path":str(chunk_path),"transcript_length":len(transcript)},"timestamp":int(time_module.time()*1000)}) + '\n')
            except:
                pass
            # #endregion
            print(f"✅ Transcribed: {Path(chunk_path).name}")
        except Exception as e:
            # #region agent log
            try:
                import json as json_module
                import time as time_module
                import traceback as tb_module
                with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                    f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"T5","location":"transcribe_chunks.py:54","message":"Chunk transcription failed","data":{"chunk_index":i,"chunk_path":str(chunk_path),"error_type":type(e).__name__,"error_message":str(e),"traceback":tb_module.format_exc()},"timestamp":int(time_module.time()*1000)}) + '\n')
            except:
                pass
            # #endregion
            print(f"❌ Failed to transcribe {chunk_path}: {e}")
            # Add empty transcript to maintain order
            transcripts.append("")
    
    return transcripts

def process_all_chunks():
    """Loop through audio chunks and transcribe each"""
    # Get all video ID folders in the chunks directory
    video_folders = [f for f in os.listdir(CHUNKS_DIR) 
                    if os.path.isdir(os.path.join(CHUNKS_DIR, f))]
    
    print(f" Found {len(video_folders)} video folders to process")
    
    for video_id in video_folders:
        video_chunks_dir = os.path.join(CHUNKS_DIR, video_id)
        video_transcript_dir = os.path.join(TRANSCRIPTS_DIR, video_id)
        
        # Create transcript directory for this video
        os.makedirs(video_transcript_dir, exist_ok=True)
        
        # Get all MP3 files in this video's chunk folder
        chunk_files = [f for f in os.listdir(video_chunks_dir) if f.endswith(".mp3")]
        chunk_files.sort()  # Ensure proper order
        
        print(f"\n📹 Processing video: {video_id} ({len(chunk_files)} chunks)")
        
        for chunk_file in chunk_files:
            chunk_path = os.path.join(video_chunks_dir, chunk_file)
            
            # Create transcript path
            transcript_file = chunk_file.replace(".mp3", ".txt")
            transcript_path = os.path.join(video_transcript_dir, transcript_file)
            
            if os.path.exists(transcript_path):
                print(f"  ⏩ Already transcribed: {chunk_file}")
                continue
            
            print(f"  📝 Transcribing: {chunk_file}")
            try:
                transcript = transcribe_chunk(chunk_path)
                with open(transcript_path, "w", encoding="utf-8") as f:
                    f.write(transcript)
                print(f"  ✅ Saved: {transcript_path}")
            except Exception as e:
                print(f"  ❌ Failed: {chunk_file} – {e}")
                with open("transcription_errors.log", "a") as log:
                    log.write(f"{video_id}/{chunk_file}: {e}\n")

if __name__ == "__main__":
    process_all_chunks()
