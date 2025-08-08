#!/usr/bin/env python3
"""
YouTube Video Processing Pipeline
================================

This script orchestrates the entire process from downloading YouTube videos
to extracting insights from the presentations.

Pipeline steps:
1. Download audio from YouTube videos
2. Split audio into chunks for processing
3. Transcribe audio chunks
4. Assemble transcripts
5. Extract insights using LLM
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import local modules
from download_audio import download_audio, check_yt_dlp
from split_audio import split_audio_file
from transcribe_chunks import transcribe_audio_chunks
from assemble_transcripts import assemble_transcript
from extact_insights import extract_insights_from_transcript

class VideoProcessingPipeline:
    """Main pipeline class for processing YouTube videos"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.video_ids_path = self.project_root / "src" / "scraper" / "data" / "video_ids.json"
        self.audio_dir = self.project_root / "src" / "transcript" / "data" / "audio"
        self.chunks_dir = self.project_root / "src" / "transcript" / "data" / "audio_chunks"
        self.transcripts_dir = self.project_root / "src" / "transcript" / "data" / "raw_transcripts"
        self.insights_dir = self.project_root / "data" / "insights"
        
        # Create necessary directories
        for directory in [self.audio_dir, self.chunks_dir, self.transcripts_dir, self.insights_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def load_video_ids(self) -> List[str]:
        """Load video IDs from the JSON file"""
        try:
            with open(self.video_ids_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Video IDs file not found: {self.video_ids_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Error reading video IDs file: {e}")
            sys.exit(1)
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        print("🔍 Checking dependencies...")
        
        # Check yt-dlp
        if not check_yt_dlp():
            print("❌ yt-dlp is not installed. Please install it with: pip install yt-dlp")
            return False
        
        # Check if required Python modules are available
        try:
            import whisper
            print("✅ Whisper available")
        except ImportError:
            print("❌ Whisper not installed. Please install it with: pip install openai-whisper")
            return False
        
        print("✅ All dependencies available")
        return True
    
    def process_single_video(self, video_id: str, force_redownload: bool = False) -> Dict[str, Any]:
        """Process a single video through the entire pipeline"""
        print(f"\n🎬 Processing video: {video_id}")
        print("-" * 50)
        
        result = {
            "video_id": video_id,
            "status": "processing",
            "steps": {},
            "errors": []
        }
        
        # Step 1: Download audio
        print("📥 Step 1: Downloading audio...")
        audio_path = self.audio_dir / f"{video_id}.mp3"
        
        if not audio_path.exists() or force_redownload:
            if download_audio(video_id):
                result["steps"]["download"] = "success"
                print("✅ Audio downloaded successfully")
            else:
                result["steps"]["download"] = "failed"
                result["errors"].append("Failed to download audio")
                result["status"] = "failed"
                return result
        else:
            result["steps"]["download"] = "skipped"
            print("⏭️  Audio already exists, skipping download")
        
        # Step 2: Split audio into chunks
        print("✂️  Step 2: Splitting audio into chunks...")
        chunks_dir = self.chunks_dir / video_id
        chunks_dir.mkdir(exist_ok=True)
        
        try:
            chunk_files = split_audio_file(str(audio_path), str(chunks_dir))
            result["steps"]["split"] = "success"
            result["steps"]["chunk_count"] = len(chunk_files)
            print(f"✅ Split into {len(chunk_files)} chunks")
        except Exception as e:
            result["steps"]["split"] = "failed"
            result["errors"].append(f"Failed to split audio: {str(e)}")
            result["status"] = "failed"
            return result
        
        # Step 3: Transcribe chunks
        print("🎤 Step 3: Transcribing audio chunks...")
        try:
            transcript_chunks = transcribe_audio_chunks(chunk_files)
            result["steps"]["transcribe"] = "success"
            result["steps"]["transcript_chunks"] = len(transcript_chunks)
            print(f"✅ Transcribed {len(transcript_chunks)} chunks")
        except Exception as e:
            result["steps"]["transcribe"] = "failed"
            result["errors"].append(f"Failed to transcribe: {str(e)}")
            result["status"] = "failed"
            return result
        
        # Step 4: Assemble transcript
        print("📝 Step 4: Assembling transcript...")
        try:
            full_transcript = assemble_transcript(transcript_chunks)
            transcript_path = self.transcripts_dir / f"{video_id}.txt"
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(full_transcript)
            
            result["steps"]["assemble"] = "success"
            result["steps"]["transcript_path"] = str(transcript_path)
            result["steps"]["transcript_length"] = len(full_transcript)
            print(f"✅ Transcript assembled ({len(full_transcript)} characters)")
        except Exception as e:
            result["steps"]["assemble"] = "failed"
            result["errors"].append(f"Failed to assemble transcript: {str(e)}")
            result["status"] = "failed"
            return result
        
        # Step 5: Extract insights
        print("🧠 Step 5: Extracting insights...")
        try:
            insights = extract_insights_from_transcript(full_transcript, video_id)
            insights_path = self.insights_dir / f"{video_id}_insights.json"
            
            with open(insights_path, 'w', encoding='utf-8') as f:
                json.dump(insights, f, indent=2, ensure_ascii=False)
            
            result["steps"]["insights"] = "success"
            result["steps"]["insights_path"] = str(insights_path)
            print("✅ Insights extracted successfully")
        except Exception as e:
            result["steps"]["insights"] = "failed"
            result["errors"].append(f"Failed to extract insights: {str(e)}")
            print(f"⚠️  Insights extraction failed: {e}")
            # Don't fail the entire pipeline for insights failure
        
        result["status"] = "completed"
        print(f"✅ Video {video_id} processing completed!")
        return result
    
    def run_pipeline(self, force_redownload: bool = False, video_ids: List[str] = None) -> Dict[str, Any]:
        """Run the complete pipeline for all videos or specified videos"""
        print("🚀 Starting YouTube Video Processing Pipeline")
        print("=" * 60)
        
        # Check dependencies
        if not self.check_dependencies():
            return {"status": "failed", "error": "Dependencies not met"}
        
        # Load video IDs
        if video_ids is None:
            video_ids = self.load_video_ids()
        
        print(f"📋 Processing {len(video_ids)} videos")
        print(f"📁 Audio directory: {self.audio_dir}")
        print(f"📁 Transcripts directory: {self.transcripts_dir}")
        print(f"📁 Insights directory: {self.insights_dir}")
        print("-" * 60)
        
        # Process each video
        results = []
        start_time = time.time()
        
        for i, video_id in enumerate(video_ids, 1):
            print(f"\n[{i}/{len(video_ids)}] ", end="")
            result = self.process_single_video(video_id, force_redownload)
            results.append(result)
            
            # Add a small delay between videos to be respectful
            if i < len(video_ids):
                time.sleep(2)
        
        # Generate summary
        end_time = time.time()
        processing_time = end_time - start_time
        
        summary = {
            "status": "completed",
            "total_videos": len(video_ids),
            "processing_time_seconds": processing_time,
            "results": results,
            "successful": len([r for r in results if r["status"] == "completed"]),
            "failed": len([r for r in results if r["status"] == "failed"])
        }
        
        # Save summary
        summary_path = self.insights_dir / "pipeline_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Print final summary
        print("\n" + "=" * 60)
        print("📊 PIPELINE SUMMARY")
        print("=" * 60)
        print(f"Total videos processed: {summary['total_videos']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Summary saved to: {summary_path}")
        
        return summary

def main():
    """Main function to run the pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Video Processing Pipeline")
    parser.add_argument("--force-redownload", action="store_true", 
                       help="Force re-download of audio files even if they exist")
    parser.add_argument("--video-ids", nargs="+", 
                       help="Specific video IDs to process (default: all from video_ids.json)")
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = VideoProcessingPipeline()
    summary = pipeline.run_pipeline(
        force_redownload=args.force_redownload,
        video_ids=args.video_ids
    )
    
    if summary["status"] == "completed":
        print("\n🎉 Pipeline completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Pipeline failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
