#!/usr/bin/env python3
"""
Test script for the YouTube Video Processing Pipeline
===================================================

This script tests the pipeline with a single video to ensure all components work correctly.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

def test_dependencies():
    """Test if all required dependencies are available"""
    print("🔍 Testing dependencies...")
    
    # Test yt-dlp
    try:
        import subprocess
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ yt-dlp available")
        else:
            print("❌ yt-dlp not available")
            return False
    except Exception as e:
        print(f"❌ yt-dlp error: {e}")
        return False
    
    # Test OpenAI
    try:
        from openai import OpenAI
        print("✅ OpenAI available")
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
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ffmpeg available")
        else:
            print("❌ ffmpeg not available")
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
        import json
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
    
    try:
        from download_audio import download_audio
        
        # Test download
        success = download_audio(video_id)
        if success:
            print("✅ Video download test successful")
            return True
        else:
            print("❌ Video download test failed")
            return False
    except Exception as e:
        print(f"❌ Video download test error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 YouTube Video Processing Pipeline Test")
    print("=" * 50)
    
    # Test dependencies
    if not test_dependencies():
        print("\n❌ Dependency test failed. Please install missing dependencies.")
        sys.exit(1)
    
    # Test video IDs file
    test_video_id = test_video_ids_file()
    if not test_video_id:
        print("\n❌ Video IDs file test failed.")
        sys.exit(1)
    
    # Test single video download
    if not test_single_video_download(test_video_id):
        print("\n❌ Video download test failed.")
        sys.exit(1)
    
    print("\n✅ All tests passed! The pipeline should work correctly.")
    print(f"\nTo run the full pipeline, use:")
    print(f"cd {PROJECT_ROOT}")
    print(f"python src/transcript/pipeline.py")
    print(f"\nOr to test with a specific video:")
    print(f"python src/transcript/pipeline.py --video-ids {test_video_id}")

if __name__ == "__main__":
    main()
