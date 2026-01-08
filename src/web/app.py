"""
Flask web application for visualizing YC Insight Extractor outputs
Uses HTMX for dynamic, interactive UI without JavaScript
"""
from flask import Flask, render_template, jsonify, request
from pathlib import Path
import json
from typing import Dict, List, Optional
from datetime import datetime
import sys
import threading
import subprocess
import os
import time
import re
import requests
from urllib.parse import urlparse, parse_qs

# Add project root to path
# app.py is at: src/web/app.py
# So parent.parent.parent = project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.config import get_config
from src.utils import CostTracker

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Initialize config with explicit project root
config = get_config(project_root=PROJECT_ROOT)


class DataLoader:
    """Load and manage insight data"""
    
    def __init__(self):
        self.insights_dir = config.paths.insights_dir
        self.metadata_dir = config.paths.metadata_dir
        self.transcripts_dir = config.paths.raw_transcripts_dir
    
    def get_all_videos(self) -> List[Dict]:
        """Get list of all processed videos"""
        videos = []
        
        # Get all insight files
        for insight_file in self.insights_dir.glob("*_insights.json"):
            if insight_file.name == "pipeline_summary.json":
                continue
            
            video_id = insight_file.stem.replace("_insights", "")
            
            try:
                with open(insight_file, 'r', encoding='utf-8') as f:
                    insight_data = json.load(f)
                
                # Load metadata if available
                metadata_file = self.metadata_dir / f"{video_id}.json"
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata_raw = json.load(f)
                        snippet = metadata_raw.get('snippet', {})
                        metadata = {
                            'title': snippet.get('title', 'Unknown Title'),
                            'description': snippet.get('description', ''),
                            'published_at': snippet.get('publishedAt', ''),
                            'channel_title': snippet.get('channelTitle', ''),
                            'tags': snippet.get('tags', [])
                        }
                
                # Get transcript length
                transcript_file = self.transcripts_dir / f"{video_id}.txt"
                transcript_length = 0
                if transcript_file.exists():
                    transcript_length = transcript_file.stat().st_size
                
                videos.append({
                    'video_id': video_id,
                    'title': metadata.get('title', insight_data.get('summary', 'Unknown Title')[:50]),
                    'summary': insight_data.get('summary', ''),
                    'insights_count': len(insight_data.get('insights', [])),
                    'nuggets_count': len(insight_data.get('golden_nuggets', [])),
                    'published_at': metadata.get('published_at', ''),
                    'transcript_length': transcript_length,
                    'metadata': metadata
                })
            except Exception as e:
                print(f"Error loading video {video_id}: {e}")
                continue
        
        # Sort by published date (newest first)
        videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        return videos
    
    def get_video_insights(self, video_id: str) -> Optional[Dict]:
        """Get insights for a specific video"""
        insight_file = self.insights_dir / f"{video_id}_insights.json"
        
        if not insight_file.exists():
            return None
        
        with open(insight_file, 'r', encoding='utf-8') as f:
            insight_data = json.load(f)
        
        # Load metadata
        metadata_file = self.metadata_dir / f"{video_id}.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_raw = json.load(f)
                snippet = metadata_raw.get('snippet', {})
                content_details = metadata_raw.get('contentDetails', {})
                metadata = {
                    'title': snippet.get('title', 'Unknown Title'),
                    'description': snippet.get('description', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'channel_title': snippet.get('channelTitle', ''),
                    'tags': snippet.get('tags', []),
                    'duration': content_details.get('duration', ''),
                    'view_count': metadata_raw.get('statistics', {}).get('viewCount', '0')
                }
        
        # Load transcript if available
        transcript_file = self.transcripts_dir / f"{video_id}.txt"
        transcript = None
        if transcript_file.exists():
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript = f.read()
        
        return {
            'video_id': video_id,
            'insights': insight_data,
            'metadata': metadata,
            'transcript': transcript
        }
    
    def search_insights(self, query: str) -> List[Dict]:
        """Search across all insights"""
        query_lower = query.lower()
        results = []
        
        for video in self.get_all_videos():
            video_id = video['video_id']
            video_data = self.get_video_insights(video_id)
            
            if not video_data:
                continue
            
            matches = []
            insight_data = video_data['insights']
            
            # Search in summary
            if query_lower in insight_data.get('summary', '').lower():
                matches.append('summary')
            
            # Search in insights
            for i, insight in enumerate(insight_data.get('insights', [])):
                if query_lower in insight.lower():
                    matches.append(f"insight_{i}")
            
            # Search in golden nuggets
            for i, nugget in enumerate(insight_data.get('golden_nuggets', [])):
                if query_lower in nugget.lower():
                    matches.append(f"nugget_{i}")
            
            # Search in title
            if query_lower in video_data['metadata'].get('title', '').lower():
                matches.append('title')
            
            if matches:
                results.append({
                    'video_id': video_id,
                    'title': video_data['metadata'].get('title', 'Unknown'),
                    'matches': matches,
                    'summary': insight_data.get('summary', '')[:200],
                    'video_data': video_data
                })
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        videos = self.get_all_videos()
        
        total_insights = sum(v['insights_count'] for v in videos)
        total_nuggets = sum(v['nuggets_count'] for v in videos)
        total_transcript_length = sum(v['transcript_length'] for v in videos)
        
        # Load cost data if available
        cost_file = config.paths.project_root / "data" / "costs.json"
        cost_data = {}
        if cost_file.exists():
            try:
                with open(cost_file, 'r') as f:
                    cost_data = json.load(f)
            except:
                pass
        
        return {
            'total_videos': len(videos),
            'total_insights': total_insights,
            'total_nuggets': total_nuggets,
            'total_transcript_length': total_transcript_length,
            'avg_insights_per_video': total_insights / len(videos) if videos else 0,
            'avg_nuggets_per_video': total_nuggets / len(videos) if videos else 0,
            'cost_data': cost_data.get('summary', {})
        }


# Initialize data loader
data_loader = DataLoader()

# Pipeline status tracking
pipeline_status = {
    'running': False,
    'progress': None,
    'current_video': None,
    'total_videos': 0,
    'processed': 0,
    'errors': []
}


@app.route('/')
def index():
    """Main dashboard"""
    stats = data_loader.get_statistics()
    videos = data_loader.get_all_videos()
    return render_template('dashboard.html', stats=stats, videos=videos)


@app.route('/video/<video_id>')
def video_detail(video_id: str):
    """Video detail page"""
    video_data = data_loader.get_video_insights(video_id)
    
    if not video_data:
        return render_template('error.html', message=f"Video {video_id} not found"), 404
    
    return render_template('video_detail.html', video_data=video_data)


@app.route('/api/videos')
def api_videos():
    """API endpoint for video list"""
    videos = data_loader.get_all_videos()
    return jsonify(videos)


@app.route('/api/video/<video_id>')
def api_video(video_id: str):
    """API endpoint for video insights"""
    video_data = data_loader.get_video_insights(video_id)
    
    if not video_data:
        return jsonify({'error': 'Video not found'}), 404
    
    return jsonify(video_data)


@app.route('/api/search')
def api_search():
    """API endpoint for search"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify([])
    
    results = data_loader.search_insights(query)
    return jsonify(results)


@app.route('/search')
def search():
    """Search page"""
    query = request.args.get('q', '')
    results = []
    
    if query:
        results = data_loader.search_insights(query)
    
    return render_template('search.html', query=query, results=results)


@app.route('/stats')
def stats():
    """Statistics page"""
    stats_data = data_loader.get_statistics()
    videos = data_loader.get_all_videos()
    return render_template('stats.html', stats=stats_data, videos=videos)


@app.route('/costs')
def costs():
    """Cost tracking page"""
    cost_file = config.paths.project_root / "data" / "costs.json"
    cost_data = {}
    
    if cost_file.exists():
        try:
            with open(cost_file, 'r') as f:
                cost_data = json.load(f)
        except:
            pass
    
    return render_template('costs.html', cost_data=cost_data)


@app.route('/repository')
def repository():
    """Repository view - browse insights folder structure"""
    insights_dir = config.paths.insights_dir
    transcripts_dir = config.paths.raw_transcripts_dir
    chunks_dir = config.paths.chunks_dir
    audio_dir = config.paths.audio_dir
    
    # Debug: Check if directory exists
    print(f"DEBUG: Insights directory: {insights_dir}")
    print(f"DEBUG: Directory exists: {insights_dir.exists()}")
    print(f"DEBUG: Project root: {config.paths.project_root}")
    
    # Get all insight files with metadata
    insight_files = []
    
    # Get all JSON files in insights directory
    if not insights_dir.exists():
        print(f"ERROR: Insights directory does not exist: {insights_dir}")
        return render_template('repository.html', 
                             insight_files=[],
                             insights_dir=insights_dir,
                             total_size=0,
                             total_transcripts_size=0,
                             total_audio_size=0)
    
    all_json_files = list(insights_dir.glob("*.json"))
    
    # Debug: print what we found
    print(f"DEBUG: Found {len(all_json_files)} JSON files in {insights_dir}")
    for f in all_json_files:
        print(f"  - {f.name}")
    
    for insight_file in sorted(all_json_files):
        # Skip pipeline_summary.json
        if insight_file.name == "pipeline_summary.json":
            continue
        
        try:
            stat = insight_file.stat()
            # Extract video_id - handle both _insights.json and other patterns
            if insight_file.name.endswith("_insights.json"):
                video_id = insight_file.stem.replace("_insights", "")
            else:
                # For other JSON files, use the stem (filename without extension)
                video_id = insight_file.stem
            
            # Check for related files
            transcript_file = transcripts_dir / f"{video_id}.txt"
            has_transcript = transcript_file.exists()
            transcript_size = transcript_file.stat().st_size if has_transcript else 0
            
            # Check for audio chunks
            video_chunks_dir = chunks_dir / video_id
            has_chunks = video_chunks_dir.exists() and any(video_chunks_dir.glob("*.mp3"))
            chunk_count = len(list(video_chunks_dir.glob("*.mp3"))) if video_chunks_dir.exists() else 0
            
            # Check for audio file
            audio_file = audio_dir / f"{video_id}.mp3"
            has_audio = audio_file.exists()
            audio_size = audio_file.stat().st_size if has_audio else 0
            
            # Load insight data for preview
            insights_count = 0
            nuggets_count = 0
            try:
                with open(insight_file, 'r', encoding='utf-8') as f:
                    insight_data = json.load(f)
                    insights_count = len(insight_data.get('insights', []))
                    nuggets_count = len(insight_data.get('golden_nuggets', []))
            except Exception as e:
                # If JSON parsing fails, still show the file but with 0 counts
                print(f"Warning: Could not parse {insight_file.name}: {e}")
                insights_count = 0
                nuggets_count = 0
            
            insight_files.append({
                'video_id': video_id,
                'filename': insight_file.name,
                'path': str(insight_file.relative_to(config.paths.project_root)),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'insights_count': insights_count,
                'nuggets_count': nuggets_count,
                'has_transcript': has_transcript,
                'transcript_size': transcript_size,
                'has_chunks': has_chunks,
                'chunk_count': chunk_count,
                'has_audio': has_audio,
                'audio_size': audio_size
            })
        except Exception as e:
            # Log error but continue processing other files
            print(f"Error processing {insight_file.name}: {e}")
            continue
    
    # Get directory statistics
    total_size = sum(f['size'] for f in insight_files)
    total_transcripts_size = sum(f['transcript_size'] for f in insight_files)
    total_audio_size = sum(f['audio_size'] for f in insight_files)
    
    return render_template('repository.html', 
                         insight_files=insight_files,
                         insights_dir=insights_dir,
                         total_size=total_size,
                         total_transcripts_size=total_transcripts_size,
                         total_audio_size=total_audio_size)


@app.route('/api/insight-file/<video_id>')
def get_insight_file(video_id: str):
    """Get raw insight JSON file"""
    insight_file = config.paths.insights_dir / f"{video_id}_insights.json"
    
    if not insight_file.exists():
        return jsonify({'error': 'Insight file not found'}), 404
    
    try:
        with open(insight_file, 'r', encoding='utf-8') as f:
            insight_data = json.load(f)
        return jsonify(insight_data)
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500


@app.route('/insight-file/<video_id>')
def view_insight_file(video_id: str):
    """View insight JSON file in formatted view"""
    insight_file = config.paths.insights_dir / f"{video_id}_insights.json"
    
    if not insight_file.exists():
        return render_template('error.html', message=f"Insight file not found for video {video_id}"), 404
    
    try:
        with open(insight_file, 'r', encoding='utf-8') as f:
            insight_data = json.load(f)
        
        # Get video metadata if available
        metadata_file = config.paths.metadata_dir / f"{video_id}.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_raw = json.load(f)
                snippet = metadata_raw.get('snippet', {})
                metadata = {
                    'title': snippet.get('title', 'Unknown Title'),
                    'published_at': snippet.get('publishedAt', ''),
                }
        
        return render_template('insight_file.html', 
                             video_id=video_id,
                             insight_data=insight_data,
                             metadata=metadata,
                             json_string=json.dumps(insight_data, indent=2, ensure_ascii=False))
    except Exception as e:
        return render_template('error.html', message=f"Error reading file: {str(e)}"), 500


def extract_video_id(url_or_id: str) -> Optional[str]:
    """Extract video ID from YouTube URL or return the ID if already provided"""
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


def check_youtube_api() -> Dict[str, any]:
    """Check if YouTube API is working"""
    api_key = config.api.google_api_key or os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        return {
            'status': 'error',
            'message': 'YouTube API key not configured',
            'configured': False
        }
    
    # Test with a simple API call (get video info for a known video)
    test_video_id = "dQw4w9WgXcQ"  # Rick Roll - always available
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet",
        "id": test_video_id,
        "key": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                return {
                    'status': 'success',
                    'message': 'YouTube API is working correctly',
                    'configured': True,
                    'test_video_title': data['items'][0]['snippet']['title']
                }
            else:
                return {
                    'status': 'error',
                    'message': 'API responded but no data returned',
                    'configured': True
                }
        elif response.status_code == 403:
            error_data = response.json()
            error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
            if "quotaExceeded" in error_reason:
                return {
                    'status': 'error',
                    'message': 'YouTube API quota exceeded',
                    'configured': True
                }
            elif "keyInvalid" in error_reason:
                return {
                    'status': 'error',
                    'message': 'Invalid YouTube API key',
                    'configured': True
                }
            else:
                return {
                    'status': 'error',
                    'message': f'API access denied: {error_reason}',
                    'configured': True
                }
        else:
            return {
                'status': 'error',
                'message': f'API returned status code {response.status_code}',
                'configured': True
            }
    except requests.exceptions.Timeout:
        return {
            'status': 'error',
            'message': 'YouTube API request timed out',
            'configured': True
        }
    except requests.exceptions.RequestException as e:
        return {
            'status': 'error',
            'message': f'Network error: {str(e)}',
            'configured': True
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}',
            'configured': True
        }


def add_video_ids(video_inputs: List[str]) -> Dict[str, any]:
    """Add new video IDs to the video_ids.json file"""
    video_ids_path = config.paths.video_ids_path
    
    # Load existing video IDs
    existing_video_ids = []
    if video_ids_path.exists():
        try:
            with open(video_ids_path, 'r', encoding='utf-8') as f:
                existing_video_ids = json.load(f)
        except:
            existing_video_ids = []
    
    # Extract video IDs from inputs (URLs or IDs)
    new_video_ids = []
    invalid_inputs = []
    
    for input_str in video_inputs:
        input_str = input_str.strip()
        if not input_str:
            continue
        
        video_id = extract_video_id(input_str)
        if video_id:
            if video_id not in existing_video_ids:
                new_video_ids.append(video_id)
        else:
            invalid_inputs.append(input_str)
    
    # Add new IDs to the list
    if new_video_ids:
        existing_video_ids.extend(new_video_ids)
        
        # Save updated list
        video_ids_path.parent.mkdir(parents=True, exist_ok=True)
        with open(video_ids_path, 'w', encoding='utf-8') as f:
            json.dump(existing_video_ids, f, indent=2)
    
    return {
        'success': True,
        'added': len(new_video_ids),
        'new_video_ids': new_video_ids,
        'invalid': len(invalid_inputs),
        'invalid_inputs': invalid_inputs,
        'total_videos': len(existing_video_ids)
    }


def get_new_videos() -> List[str]:
    """Get list of video IDs that haven't been processed yet"""
    # Load all video IDs from the scraper
    video_ids_path = config.paths.video_ids_path
    
    if not video_ids_path.exists():
        return []
    
    try:
        with open(video_ids_path, 'r', encoding='utf-8') as f:
            all_video_ids = json.load(f)
    except:
        return []
    
    # Get list of already processed videos (those with insight files)
    processed_videos = set()
    for insight_file in config.paths.insights_dir.glob("*_insights.json"):
        if insight_file.name == "pipeline_summary.json":
            continue
        video_id = insight_file.stem.replace("_insights", "")
        processed_videos.add(video_id)
    
    # Find new videos
    new_videos = [vid for vid in all_video_ids if vid not in processed_videos]
    
    return new_videos


def run_pipeline_for_new_videos():
    """Run pipeline for new videos in a background thread"""
    global pipeline_status
    
    if pipeline_status['running']:
        return
    
    pipeline_status['running'] = True
    pipeline_status['errors'] = []
    pipeline_status['processed'] = 0
    
    new_videos = get_new_videos()
    
    if not new_videos:
        pipeline_status['running'] = False
        pipeline_status['progress'] = "No new videos to process"
        return
    
    pipeline_status['total_videos'] = len(new_videos)
    pipeline_status['current_video'] = None
    pipeline_status['progress'] = f"Found {len(new_videos)} new videos to process"
    
    # Run pipeline in subprocess (better for isolation and error handling)
    def run_pipeline():
        try:
            # Build command
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "src" / "transcript" / "pipeline.py"),
                "--video-ids"
            ] + new_videos
            
            # Run pipeline
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(PROJECT_ROOT),
                bufsize=1  # Line buffered
            )
            
            # Monitor progress by checking output
            pipeline_status['progress'] = "Starting pipeline..."
            
            # Wait for completion
            stdout, stderr = process.communicate()
            
            # Update status based on completion
            if process.returncode == 0:
                pipeline_status['progress'] = f"✅ Successfully processed {len(new_videos)} videos"
                pipeline_status['processed'] = len(new_videos)
            else:
                error_msg = stderr if stderr else "Unknown error"
                pipeline_status['errors'].append(f"Pipeline failed: {error_msg}")
                pipeline_status['progress'] = f"❌ Pipeline completed with errors"
            
            pipeline_status['current_video'] = None
            
        except Exception as e:
            pipeline_status['errors'].append(str(e))
            pipeline_status['progress'] = f"❌ Error: {str(e)}"
        finally:
            pipeline_status['running'] = False
    
    # Start in background thread
    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()


@app.route('/pipeline')
def pipeline_page():
    """Pipeline management page"""
    new_videos = get_new_videos()
    processed_videos = data_loader.get_all_videos()
    youtube_api_status = check_youtube_api()
    
    return render_template('pipeline.html', 
                         new_videos=new_videos,
                         processed_count=len(processed_videos),
                         status=pipeline_status,
                         youtube_api_status=youtube_api_status)


@app.route('/api/pipeline/status')
def pipeline_status_api():
    """Get current pipeline status"""
    return jsonify(pipeline_status)


@app.route('/api/pipeline/start', methods=['POST'])
def start_pipeline():
    """Start processing new videos"""
    if pipeline_status['running']:
        return jsonify({'error': 'Pipeline is already running'}), 400
    
    new_videos = get_new_videos()
    
    if not new_videos:
        return jsonify({
            'message': 'No new videos to process',
            'new_videos': []
        })
    
    # Start pipeline
    run_pipeline_for_new_videos()
    
    return jsonify({
        'message': f'Started processing {len(new_videos)} new videos',
        'new_videos': new_videos,
        'status': pipeline_status
    })


@app.route('/api/pipeline/new-videos')
def get_new_videos_api():
    """Get list of new videos that need processing"""
    new_videos = get_new_videos()
    
    # Get metadata for new videos if available
    videos_with_metadata = []
    for video_id in new_videos:
        metadata_file = config.paths.metadata_dir / f"{video_id}.json"
        metadata = {}
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_raw = json.load(f)
                    snippet = metadata_raw.get('snippet', {})
                    metadata = {
                        'title': snippet.get('title', 'Unknown Title'),
                        'published_at': snippet.get('publishedAt', ''),
                    }
            except:
                pass
        
        videos_with_metadata.append({
            'video_id': video_id,
            'metadata': metadata
        })
    
    return jsonify({
        'count': len(new_videos),
        'videos': videos_with_metadata
    })


@app.route('/api/pipeline/add-videos', methods=['POST'])
def add_videos_api():
    """Add new video IDs or URLs to the processing queue"""
    data = request.get_json()
    
    if not data or 'videos' not in data:
        return jsonify({'error': 'No videos provided'}), 400
    
    video_inputs = data['videos']
    if isinstance(video_inputs, str):
        # Single video provided as string
        video_inputs = [video_inputs]
    
    result = add_video_ids(video_inputs)
    
    if result['invalid'] > 0:
        return jsonify({
            'success': True,
            'message': f"Added {result['added']} videos. {result['invalid']} invalid inputs.",
            'added': result['added'],
            'new_video_ids': result['new_video_ids'],
            'invalid_inputs': result['invalid_inputs'],
            'total_videos': result['total_videos']
        }), 200
    
    return jsonify({
        'success': True,
        'message': f"Successfully added {result['added']} new video(s)",
        'added': result['added'],
        'new_video_ids': result['new_video_ids'],
        'total_videos': result['total_videos']
    })


@app.route('/api/youtube-api/check')
def check_youtube_api_route():
    """Check YouTube API status"""
    status = check_youtube_api()
    return jsonify(status)


@app.route('/partial/video-card/<video_id>')
def partial_video_card(video_id: str):
    """HTMX partial: Video card"""
    video_data = data_loader.get_video_insights(video_id)
    
    if not video_data:
        return "<div>Video not found</div>", 404
    
    return render_template('partials/video_card.html', video_data=video_data)


if __name__ == '__main__':
    print("🚀 Starting YC Insight Extractor Web Interface")
    print(f"📁 Insights directory: {config.paths.insights_dir}")
    print(f"🌐 Server running at http://localhost:5012")
    print("Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5012)
