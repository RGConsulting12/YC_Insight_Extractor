#!/usr/bin/env python3
"""
Test script for the YouTube Video Processing Pipeline
===================================================

This script tests the pipeline with a single video to ensure all components work correctly.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

def test_dependencies(require_all=False):
    """Test if all required dependencies are available
    
    Args:
        require_all: If True, all dependencies must be available. If False, warnings only.
    
    Returns:
        bool: True if all required dependencies are available (or if require_all=False)
    """
    print("🔍 Testing dependencies...")
    all_available = True
    
    # Test yt-dlp (use check_yt_dlp from download_audio if available)
    yt_dlp_available = False
    try:
        from download_audio import check_yt_dlp
        if check_yt_dlp():
            print("✅ yt-dlp available")
            yt_dlp_available = True
        else:
            print("❌ yt-dlp not available")
            if require_all:
                all_available = False
    except ImportError:
        # Fallback to direct check if import fails
        try:
            result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ yt-dlp available")
                yt_dlp_available = True
            else:
                print("❌ yt-dlp not available")
                if require_all:
                    all_available = False
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"❌ yt-dlp error: {e}")
            if require_all:
                all_available = False
    
    if not yt_dlp_available and not require_all:
        print("⚠️  Warning: yt-dlp is required for downloading videos")
    
    # Test OpenAI
    try:
        from openai import OpenAI
        print("✅ OpenAI available")
        
        # Check if API key is set
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  Warning: OPENAI_API_KEY not set in environment")
            print("   The pipeline will fail without this key")
        else:
            print("✅ OPENAI_API_KEY is set")
    except ImportError:
        print("❌ OpenAI not installed")
        return False
    
    # Test python-dotenv
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv available")
    except ImportError:
        print("❌ python-dotenv not installed")
        return False
    
    # Test ffmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ ffmpeg available")
        else:
            print("❌ ffmpeg not available")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"❌ ffmpeg error: {e}")
        return False
    except Exception as e:
        print(f"❌ ffmpeg error: {e}")
        return False
    
    return True

def test_video_ids_file():
    """Test if video IDs file exists and is valid"""
    print("\n📋 Testing video IDs file...")
    
    video_ids_path = PROJECT_ROOT / "src" / "scraper" / "data" / "video_ids.json"
    
    if not video_ids_path.exists():
        print(f"❌ Video IDs file not found: {video_ids_path}")
        return False
    
    try:
        with open(video_ids_path, 'r') as f:
            video_ids = json.load(f)
        
        if isinstance(video_ids, list) and len(video_ids) > 0:
            print(f"✅ Video IDs file valid with {len(video_ids)} videos")
            return video_ids[0]  # Return first video ID for testing
        else:
            print("❌ Video IDs file is empty or invalid")
            return False
    except Exception as e:
        print(f"❌ Error reading video IDs file: {e}")
        return False

def test_single_video_download(video_id):
    """Test downloading a single video"""
    print(f"\n📥 Testing video download: {video_id}")
    
    # First check if yt-dlp is available
    yt_dlp_available = False
    try:
        from download_audio import check_yt_dlp
        yt_dlp_available = check_yt_dlp()
        if not yt_dlp_available:
            print("❌ yt-dlp is not available. Cannot test download.")
            print("   Install with: pip install yt-dlp")
            return False
    except ImportError:
        # Try direct check
        try:
            result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=5)
            yt_dlp_available = (result.returncode == 0)
            if not yt_dlp_available:
                print("❌ yt-dlp is not available. Cannot test download.")
                print("   Install with: pip install yt-dlp")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            print("❌ yt-dlp is not available. Cannot test download.")
            print("   Install with: pip install yt-dlp")
            return False
    
    try:
        from download_audio import download_audio
        
        # Test download
        success = download_audio(video_id)
        if success:
            # Verify the file was actually created
            audio_dir = PROJECT_ROOT / "src" / "transcript" / "data" / "audio"
            audio_file = audio_dir / f"{video_id}.mp3"
            
            if audio_file.exists() and audio_file.stat().st_size > 0:
                file_size_mb = audio_file.stat().st_size / (1024 * 1024)
                print(f"✅ Video download test successful")
                print(f"   File size: {file_size_mb:.2f} MB")
                return True
            else:
                print("❌ Download reported success but file is missing or empty")
                return False
        else:
            print("❌ Video download test failed")
            return False
    except Exception as e:
        print(f"❌ Video download test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def extract_video_id_from_url(url_or_id):
    """Extract video ID from YouTube URL or return the ID if already provided"""
    import re
    
    # If it's already just an ID (11 characters, alphanumeric)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Try to extract from various YouTube URL formats
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test YouTube Video Processing Pipeline")
    parser.add_argument("--video-id", type=str, help="Specific video ID or URL to test (optional)")
    parser.add_argument("--skip-download", action="store_true", help="Skip the download test")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency checks (only test video ID extraction)")
    
    args = parser.parse_args()
    
    print("🧪 YouTube Video Processing Pipeline Test")
    print("=" * 50)
    
    # Test dependencies (only fail if not skipping and require_all=True)
    if not args.skip_deps:
        deps_ok = test_dependencies(require_all=not args.skip_download)
        if not deps_ok and not args.skip_download:
            print("\n❌ Dependency test failed. Please install missing dependencies.")
            print("   Use --skip-deps to skip dependency checks")
            sys.exit(1)
    else:
        print("⏭️  Skipping dependency checks (--skip-deps flag set)")
    
    # Determine which video ID to test
    if args.video_id:
        # Extract video ID from URL if needed
        test_video_id = extract_video_id_from_url(args.video_id)
        if not test_video_id:
            print(f"\n❌ Invalid video ID or URL: {args.video_id}")
            print("   Expected format: VIDEO_ID or https://www.youtube.com/watch?v=VIDEO_ID")
            sys.exit(1)
        print(f"\n📹 Using provided video ID: {test_video_id}")
    else:
        # Test video IDs file
        test_video_id = test_video_ids_file()
        if not test_video_id:
            print("\n❌ Video IDs file test failed.")
            print("   Use --video-id to specify a video to test")
            sys.exit(1)
        print(f"\n📹 Using video ID from file: {test_video_id}")
    
    # Test single video download
    if not args.skip_download:
        download_result = test_single_video_download(test_video_id)
        if not download_result:
            print("\n❌ Video download test failed.")
            if args.skip_deps:
                print("   Note: yt-dlp may not be installed. Install it with: pip install yt-dlp")
            sys.exit(1)
    else:
        print("\n⏭️  Skipping download test (--skip-download flag set)")
    
    print("\n✅ All tests passed! The pipeline should work correctly.")
    print(f"\nTo run the full pipeline, use:")
    print(f"cd {PROJECT_ROOT}")
    print(f"python src/transcript/pipeline.py")
    print(f"\nOr to test with a specific video:")
    print(f"python src/transcript/pipeline.py --video-ids {test_video_id}")

if __name__ == "__main__":
    main()
