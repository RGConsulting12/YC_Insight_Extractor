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
import re # Added for speaker name extraction

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import local modules
from download_audio import download_audio, check_yt_dlp
from split_audio import split_audio_file
from transcribe_chunks import transcribe_audio_chunks
from assemble_transcripts import assemble_transcript
from extract_insights import extract_insights_from_transcript

class VideoProcessingPipeline:
    """Main pipeline class for processing YouTube videos"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.video_ids_path = self.project_root / "src" / "scraper" / "data" / "video_ids.json"
        self.audio_dir = self.project_root / "src" / "transcript" / "data" / "audio"
        self.chunks_dir = self.project_root / "src" / "transcript" / "data" / "audio_chunks"
        self.transcripts_dir = self.project_root / "src" / "transcript" / "data" / "raw_transcripts"
        self.insights_dir = self.project_root / "src" / "transcript" / "data" / "insights"
        
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
        
        # Check OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY not found in environment variables")
            print("Please set it in your .env file")
            return False
        
        # Check if required Python modules are available
        try:
            from openai import OpenAI
            print("✅ OpenAI client available")
        except ImportError:
            print("❌ OpenAI client not installed. Please install it with: pip install openai")
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
        
        # Load video metadata for context
        video_metadata = self.load_video_metadata(video_id)
        if video_metadata:
            result["video_metadata"] = {
                "title": video_metadata.get("snippet", {}).get("title", ""),
                "description": video_metadata.get("snippet", {}).get("description", ""),
                "tags": video_metadata.get("snippet", {}).get("tags", []),
                "channel_title": video_metadata.get("snippet", {}).get("channelTitle", ""),
                "duration": video_metadata.get("contentDetails", {}).get("duration", ""),
                "published_at": video_metadata.get("snippet", {}).get("publishedAt", "")
            }
            print(f"�� Loaded metadata: {result['video_metadata']['title'][:50]}...")
        
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
        
        # Check if chunks already exist
        chunk_files = list(chunks_dir.glob(f"{video_id}_chunk_*.mp3"))
        metadata_path = chunks_dir / f"{video_id}_chunks_metadata.json"
        
        if chunk_files and metadata_path.exists() and not force_redownload:
            result["steps"]["split"] = "skipped"
            result["steps"]["chunk_count"] = len(chunk_files)
            print(f"⏭️  Chunks already exist ({len(chunk_files)} chunks), skipping split")
            
            # Load existing chunk metadata
            with open(metadata_path, 'r') as f:
                chunk_metadata = json.load(f)
            result["steps"]["chunk_metadata"] = chunk_metadata
            print(f"📊 Loaded existing metadata for {len(chunk_metadata)} chunks")
        else:
            try:
                chunk_files = split_audio_file(str(audio_path), str(chunks_dir))
                result["steps"]["split"] = "success"
                result["steps"]["chunk_count"] = len(chunk_files)
                print(f"✅ Split into {len(chunk_files)} chunks")
                
                # Load chunk metadata for later use
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        chunk_metadata = json.load(f)
                    result["steps"]["chunk_metadata"] = chunk_metadata
                    print(f"📊 Loaded metadata for {len(chunk_metadata)} chunks")
                
            except Exception as e:
                result["steps"]["split"] = "failed"
                result["errors"].append(f"Failed to split audio: {str(e)}")
                result["status"] = "failed"
                return result
        
        # Step 3: Transcribe chunks
        print("🎤 Step 3: Transcribing audio chunks...")

        # Check if transcripts already exist in the chunk_transcripts directory
        chunk_transcripts_dir = self.project_root / "src" / "transcript" / "data" / "chunk_transcripts" / video_id
        transcript_chunks = []

        if chunk_transcripts_dir.exists():
            # Look for existing transcript files
            existing_transcripts = list(chunk_transcripts_dir.glob(f"{video_id}_chunk_*.txt"))
            existing_transcripts.sort()  # Ensure proper order
            
            if existing_transcripts and len(existing_transcripts) > 0 and not force_redownload:
                # Load existing transcripts
                for transcript_file in existing_transcripts:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        transcript_chunks.append(f.read().strip())
                
                result["steps"]["transcribe"] = "skipped"
                result["steps"]["transcript_chunks"] = len(transcript_chunks)
                print(f"⏭️  Transcripts already exist ({len(transcript_chunks)} chunks), skipping transcription")
                
                # Load chunk metadata for enhancement
                metadata_path = chunks_dir / f"{video_id}_chunks_metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        chunk_metadata = json.load(f)
                    result["steps"]["chunk_metadata"] = chunk_metadata
                    print(f"📊 Loaded existing metadata for {len(chunk_metadata)} chunks")
            else:
                # Need to transcribe
                try:
                    transcript_chunks = transcribe_audio_chunks(chunk_files)
                    result["steps"]["transcribe"] = "success"
                    result["steps"]["transcript_chunks"] = len(transcript_chunks)
                    print(f"✅ Transcribed {len(transcript_chunks)} chunks")
                    
                    # Load chunk metadata for enhancement
                    metadata_path = chunks_dir / f"{video_id}_chunks_metadata.json"
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            chunk_metadata = json.load(f)
                        result["steps"]["chunk_metadata"] = chunk_metadata
                        print(f"📊 Loaded metadata for {len(chunk_metadata)} chunks")
                        
                except Exception as e:
                    result["steps"]["transcribe"] = "failed"
                    result["errors"].append(f"Failed to transcribe: {str(e)}")
                    result["status"] = "failed"
                    return result
        else:
            # No transcript directory exists, need to transcribe
            try:
                transcript_chunks = transcribe_audio_chunks(chunk_files)
                result["steps"]["transcribe"] = "success"
                result["steps"]["transcript_chunks"] = len(transcript_chunks)
                print(f"✅ Transcribed {len(transcript_chunks)} chunks")
                
                # Load chunk metadata for enhancement
                metadata_path = chunks_dir / f"{video_id}_chunks_metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        chunk_metadata = json.load(f)
                    result["steps"]["chunk_metadata"] = chunk_metadata
                    print(f"📊 Loaded metadata for {len(chunk_metadata)} chunks")
                    
            except Exception as e:
                result["steps"]["transcribe"] = "failed"
                result["errors"].append(f"Failed to transcribe: {str(e)}")
                result["status"] = "failed"
                return result
        
        # Enhance transcripts with metadata context
        if "chunk_metadata" in result["steps"]:
            enhanced_transcripts = []
            for i, (transcript, metadata) in enumerate(zip(transcript_chunks, result["steps"]["chunk_metadata"])):
                enhanced_transcript = f"""
=== CHUNK {i} ===
Time: {metadata['start_time_formatted']} - {metadata['end_time_formatted']}
Duration: {metadata['duration_seconds']} seconds
{metadata.get('chapter_title', f'Chunk {i}')}

{transcript}
"""
                enhanced_transcripts.append(enhanced_transcript)
            transcript_chunks = enhanced_transcripts
            print("📊 Enhanced transcripts with timing metadata")
        
        # Step 4: Assemble transcript
        print("📝 Step 4: Assembling transcript...")
        transcript_path = self.transcripts_dir / f"{video_id}.txt"
        
        if transcript_path.exists() and not force_redownload:
            result["steps"]["assemble"] = "skipped"
            with open(transcript_path, 'r', encoding='utf-8') as f:
                full_transcript = f.read()
            result["steps"]["transcript_path"] = str(transcript_path)
            result["steps"]["transcript_length"] = len(full_transcript)
            print(f"⏭️  Transcript already exists ({len(full_transcript)} characters), skipping assembly")
        else:
            try:
                full_transcript = assemble_transcript(transcript_chunks)
                
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
        
        # Step 5: Extract insights with rich context
        print("🧠 Step 5: Extracting insights...")
        insights_path = self.insights_dir / f"{video_id}_insights.json"
        
        if insights_path.exists() and not force_redownload:
            result["steps"]["insights"] = "skipped"
            result["steps"]["insights_path"] = str(insights_path)
            print(f"⏭️  Insights already exist, skipping extraction")
        else:
            try:
                # Create rich context for the LLM
                context_header = self.create_context_header(video_id, result.get("video_metadata", {}))
                
                # Combine context + transcript for better insights
                enhanced_transcript = f"{context_header}\n\n{full_transcript}"
                
                insights = extract_insights_from_transcript(enhanced_transcript, video_id)
                
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

    def load_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """Load video metadata from the scraper data"""
        metadata_path = self.project_root / "src" / "scraper" / "data" / "metadata" / f"{video_id}.json"
        
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Warning: Could not load metadata for {video_id}: {e}")
                return None
        else:
            print(f"⚠️ Warning: No metadata file found for {video_id}")
            return None

    def create_context_header(self, video_id: str, metadata: Dict[str, Any]) -> str:
        """Create a rich context header for the LLM"""
        context_parts = []
        
        if metadata.get("title"):
            context_parts.append(f"VIDEO TITLE: {metadata['title']}")
        
        if metadata.get("channel_title"):
            context_parts.append(f"CHANNEL: {metadata['channel_title']}")
        
        if metadata.get("duration"):
            context_parts.append(f"DURATION: {metadata['duration']}")
        
        if metadata.get("published_at"):
            # Convert ISO date to readable format
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(metadata['published_at'].replace('Z', '+00:00'))
                context_parts.append(f"PUBLISHED: {dt.strftime('%B %d, %Y')}")
            except:
                context_parts.append(f"PUBLISHED: {metadata['published_at']}")
        
        if metadata.get("tags"):
            context_parts.append(f"TAGS: {', '.join(metadata['tags'])}")
        
        # Extract speaker name from title/description if possible
        speaker_name = self.extract_speaker_name(metadata)
        if speaker_name:
            context_parts.append(f"SPEAKER: {speaker_name}")
        
        if metadata.get("description"):
            # Truncate description to first few sentences for context
            desc_lines = metadata['description'].split('\n')
            relevant_desc = []
            for line in desc_lines[:3]:  # First 3 lines usually contain key info
                if line.strip() and not line.startswith('http'):
                    relevant_desc.append(line.strip())
            if relevant_desc:
                context_parts.append(f"DESCRIPTION: {' '.join(relevant_desc)}")
        
        return "\n".join(context_parts)

    def extract_speaker_name(self, metadata: Dict[str, Any]) -> str:
        """Extract speaker name from title or description"""
        title = metadata.get("title", "")
        description = metadata.get("description", "")
        
        # Common patterns in YC video titles
        patterns = [
            r"\| ([^|]+)$",  # "Title | Speaker Name"
            r"by ([^|]+)$",  # "Title by Speaker Name"
            r"with ([^|]+)$", # "Title with Speaker Name"
            r"featuring ([^|]+)$", # "Title featuring Speaker Name"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1).strip()
        
        # Look for "Co-founder", "CEO", "CTO" patterns in title
        founder_patterns = [
            r"([A-Z][a-z]+ [A-Z][a-z]+) Co-founder",
            r"([A-Z][a-z]+ [A-Z][a-z]+) CEO",
            r"([A-Z][a-z]+ [A-Z][a-z]+) CTO",
        ]
        
        for pattern in founder_patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1).strip()
        
        return ""

    def estimate_cost(self, audio_duration_minutes: float, transcript_length_chars: int) -> Dict[str, float]:
        """Estimate API costs for processing"""
        whisper_cost = audio_duration_minutes * 0.006
        gpt_tokens = transcript_length_chars / 4  # Rough estimate
        gpt_cost = (gpt_tokens * 5 / 1_000_000) + (gpt_tokens * 0.1 * 15 / 1_000_000)
        
        return {
            "whisper_cost": whisper_cost,
            "gpt_cost": gpt_cost,
            "total_cost": whisper_cost + gpt_cost
        }

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
