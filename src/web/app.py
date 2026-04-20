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
from src.utils import CostTracker, ProgressTracker
from src.utils.semantic_search import SemanticSearch

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
    
    def search_insights(self, query: str, use_semantic: bool = True) -> Dict:
        """Search across all insights using RAG (semantic search + LLM answer generation) or keyword search"""
        if not query.strip():
            return {'answer': '', 'results': []}
        
        # Try semantic search first if enabled and embeddings exist
        if use_semantic:
            try:
                # #region agent log
                try:
                    import json as json_module
                    import time as time_module
                    with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                        f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"RAG6","location":"app.py:148","message":"DataLoader.search_insights() called with semantic search","data":{"query":query,"use_semantic":use_semantic},"timestamp":int(time_module.time()*1000)}) + '\n')
                except:
                    pass
                # #endregion
                
                rag_result = semantic_search.search_with_context(query, top_k=10)
                
                # #region agent log
                try:
                    import json as json_module
                    import time as time_module
                    with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                        f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"RAG7","location":"app.py:160","message":"RAG result received","data":{"query":query,"has_answer":bool(rag_result.get('answer')),"sources_count":len(rag_result.get('sources', []))},"timestamp":int(time_module.time()*1000)}) + '\n')
                except:
                    pass
                # #endregion
                
                # Convert RAG result to format expected by template
                results = []
                for source in rag_result.get('sources', []):
                    video_id = source['video_id']
                    video_data = self.get_video_insights(video_id)
                    if video_data:
                        results.append({
                            'video_id': video_id,
                            'title': video_data['metadata'].get('title', 'Unknown Title'),
                            'summary': source['text'][:200] + '...' if len(source['text']) > 200 else source['text'],
                            'matched_text': source['text'],
                            'similarity': source['similarity'],
                            'search_type': 'semantic',
                            'matches': []
                        })
                
                return {
                    'answer': rag_result.get('answer', ''),
                    'results': results
                }
            except Exception as e:
                print(f"⚠️  Semantic search error: {e}, falling back to keyword search")
                # #region agent log
                try:
                    import json as json_module
                    import time as time_module
                    with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                        f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"RAG8","location":"app.py:217","message":"Semantic search failed, falling back","data":{"query":query,"error":str(e)},"timestamp":int(time_module.time()*1000)}) + '\n')
                except:
                    pass
                # #endregion
        
        # Fallback to keyword search
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
            
            # Also search in transcript if available
            if video_data.get('transcript'):
                transcript_lower = video_data['transcript'].lower()
                if query_lower in transcript_lower:
                    matches.append('transcript')
            
            if matches:
                results.append({
                    'video_id': video_id,
                    'title': video_data['metadata'].get('title', 'Unknown'),
                    'matches': matches,
                    'summary': insight_data.get('summary', '')[:200],
                    'video_data': video_data,
                    'search_type': 'keyword'
                })
        
        return {
            'answer': f'Found {len(results)} results using keyword search.',
            'results': results
        }
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        videos = self.get_all_videos()
        
        # Safely sum with default values
        total_insights = sum(v.get('insights_count', 0) for v in videos)
        total_nuggets = sum(v.get('nuggets_count', 0) for v in videos)
        total_transcript_length = sum(v.get('transcript_length', 0) for v in videos)
        
        # Load cost data if available
        cost_file = config.paths.project_root / "data" / "costs.json"
        cost_data = {}
        if cost_file.exists():
            try:
                with open(cost_file, 'r') as f:
                    cost_data = json.load(f)
            except:
                pass
        
        num_videos = len(videos)
        return {
            'total_videos': num_videos,
            'total_insights': total_insights,
            'total_nuggets': total_nuggets,
            'total_transcript_length': total_transcript_length or 0,
            'avg_insights_per_video': total_insights / num_videos if num_videos > 0 else 0,
            'avg_nuggets_per_video': total_nuggets / num_videos if num_videos > 0 else 0,
            'cost_data': cost_data.get('summary', {})
        }


# Initialize data loader
data_loader = DataLoader()

# Initialize semantic search - use config paths for consistency
semantic_search = SemanticSearch(
    PROJECT_ROOT,
    transcripts_dir=config.paths.raw_transcripts_dir
)

# Pipeline status tracking
pipeline_status = {
    'running': False,
    'progress': None,
    'current_video': None,
    'total_videos': 0,
    'processed': 0,
    'errors': []
}

# Progress file path
PROGRESS_FILE = PROJECT_ROOT / "data" / "pipeline_progress.json"
PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)


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
    query = request.args.get('q', '').strip()
    use_semantic = request.args.get('semantic', 'true').lower() == 'true'
    
    if not query:
        return jsonify({'answer': '', 'results': []})
    
    search_result = data_loader.search_insights(query, use_semantic=use_semantic)
    return jsonify(search_result)


@app.route('/search')
def search():
    """Search page"""
    query = request.args.get('q', '').strip()
    use_semantic = request.args.get('semantic', 'true').lower() == 'true'
    search_result = {'answer': '', 'results': []}
    
    if query:
        search_result = data_loader.search_insights(query, use_semantic=use_semantic)
    
    return render_template('search.html', query=query, answer=search_result.get('answer', ''), results=search_result.get('results', []), use_semantic=use_semantic)


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
            
            # Check if embeddings exist for this video
            has_embeddings = video_id in semantic_search.embeddings_cache
            
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
                'audio_size': audio_size,
                'has_embeddings': has_embeddings
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
    
    # Initialize progress tracker
    # #region agent log
    with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
        import json as json_module
        f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"app.py:676","message":"Initializing progress tracker","data":{"progress_file":str(PROGRESS_FILE),"file_exists":PROGRESS_FILE.exists(),"new_videos_count":len(new_videos)},"timestamp":int(time.time()*1000)}) + '\n')
    # #endregion
    progress_tracker = ProgressTracker(PROGRESS_FILE)
    # #region agent log
    with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
        import json as json_module
        f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"app.py:679","message":"Progress tracker created, calling start_processing","data":{"progress_file":str(PROGRESS_FILE)},"timestamp":int(time.time()*1000)}) + '\n')
    # #endregion
    progress_tracker.start_processing(new_videos)
    # #region agent log
    with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
        import json as json_module
        f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"app.py:682","message":"start_processing completed, checking file","data":{"progress_file":str(PROGRESS_FILE),"file_exists":PROGRESS_FILE.exists(),"file_size":PROGRESS_FILE.stat().st_size if PROGRESS_FILE.exists() else 0},"timestamp":int(time.time()*1000)}) + '\n')
    # #endregion
    
    pipeline_status['total_videos'] = len(new_videos)
    pipeline_status['current_video'] = None
    pipeline_status['progress'] = f"Found {len(new_videos)} new videos to process"
    
    # Run pipeline in subprocess (better for isolation and error handling)
    def run_pipeline():
        try:
            # Build command with progress file path
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "src" / "transcript" / "pipeline.py"),
                "--video-ids"
            ] + new_videos + [
                "--progress-file",
                str(PROGRESS_FILE)
            ]
            # #region agent log
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"app.py:694","message":"Building subprocess command","data":{"cmd":cmd,"progress_file_arg":str(PROGRESS_FILE),"progress_file_exists":PROGRESS_FILE.exists()},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            
            # Run pipeline
            # #region agent log
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"app.py:697","message":"About to start subprocess","data":{"cmd":cmd,"cwd":str(PROJECT_ROOT)},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(PROJECT_ROOT),
                bufsize=1  # Line buffered
            )
            # #region agent log
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"app.py:705","message":"Subprocess started","data":{"pid":process.pid,"returncode":process.returncode},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            
            # Monitor progress by checking progress file and process output
            pipeline_status['progress'] = f"Starting pipeline... Processing {len(new_videos)} videos sequentially"
            
            # Monitor progress in real-time
            import time as time_module
            monitor_iteration = 0
            while process.poll() is None:
                monitor_iteration += 1
                # #region agent log
                with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                    import json as json_module
                    f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"app.py:713","message":"Monitoring loop iteration","data":{"iteration":monitor_iteration,"progress_file_exists":PROGRESS_FILE.exists(),"process_alive":process.poll() is None},"timestamp":int(time.time()*1000)}) + '\n')
                # #endregion
                # Check progress file for updates
                if PROGRESS_FILE.exists():
                    try:
                        # #region agent log
                        with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                            import json as json_module
                            file_stat = PROGRESS_FILE.stat()
                            f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"app.py:717","message":"Reading progress file","data":{"progress_file":str(PROGRESS_FILE),"file_size":file_stat.st_size,"file_mtime":file_stat.st_mtime},"timestamp":int(time.time()*1000)}) + '\n')
                        # #endregion
                        progress_tracker = ProgressTracker(PROGRESS_FILE)
                        progress_data = progress_tracker.get_progress()
                        # #region agent log
                        with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                            import json as json_module
                            f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"app.py:720","message":"Progress data retrieved","data":{"has_videos":'videos' in progress_data if progress_data else False,"video_count":len(progress_data.get('videos',{})) if progress_data else 0,"last_updated":progress_data.get('last_updated') if progress_data else None},"timestamp":int(time.time()*1000)}) + '\n')
                        # #endregion
                        
                        if progress_data and 'videos' in progress_data:
                            completed = sum(1 for v in progress_data['videos'].values() 
                                          if v.get('stage') == 'completed')
                            failed = sum(1 for v in progress_data['videos'].values() 
                                        if v.get('stage') == 'failed')
                            in_progress = [vid for vid, data in progress_data['videos'].items() 
                                         if data.get('stage') not in ['completed', 'failed', 'queued']]
                            
                            if in_progress:
                                current_vid = in_progress[0]
                                current_stage = progress_data['videos'][current_vid].get('stage_name', 'Processing')
                                pipeline_status['current_video'] = current_vid
                                pipeline_status['progress'] = f"Processing video {completed + failed + 1}/{len(new_videos)}: {current_stage}"
                            else:
                                pipeline_status['progress'] = f"Queued: {len(new_videos) - completed - failed} videos waiting"
                            
                            pipeline_status['processed'] = completed
                    except Exception as e:
                        # If progress file read fails, continue monitoring
                        # #region agent log
                        with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                            import json as json_module
                            import traceback
                            f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"app.py:737","message":"Exception reading progress file","data":{"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()},"timestamp":int(time.time()*1000)}) + '\n')
                        # #endregion
                        pass
                
                # Sleep briefly before checking again
                time_module.sleep(1)
            
            # Wait for final output
            # #region agent log
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"app.py:743","message":"Waiting for subprocess to complete","data":{"process_alive":process.poll() is None},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            stdout, stderr = process.communicate()
            # #region agent log
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"app.py:746","message":"Subprocess completed","data":{"returncode":process.returncode,"stdout_length":len(stdout) if stdout else 0,"stderr_length":len(stderr) if stderr else 0,"stderr_preview":stderr[:200] if stderr else None},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            
            # Final status update
            if PROGRESS_FILE.exists():
                try:
                    progress_tracker = ProgressTracker(PROGRESS_FILE)
                    progress_data = progress_tracker.get_progress()
                    if progress_data and 'videos' in progress_data:
                        completed = sum(1 for v in progress_data['videos'].values() 
                                      if v.get('stage') == 'completed')
                        failed = sum(1 for v in progress_data['videos'].values() 
                                    if v.get('stage') == 'failed')
                        pipeline_status['processed'] = completed
                except:
                    pass
            
            # Update status based on completion
            if process.returncode == 0:
                pipeline_status['progress'] = f"✅ Successfully processed {pipeline_status.get('processed', len(new_videos))} videos"
            else:
                error_msg = stderr if stderr else stdout if stdout else "Unknown error"
                pipeline_status['errors'].append(f"Pipeline failed: {error_msg[:500]}")
                pipeline_status['progress'] = f"❌ Pipeline completed with errors"
            
            pipeline_status['current_video'] = None
            
        except Exception as e:
            pipeline_status['errors'].append(str(e))
            pipeline_status['progress'] = f"❌ Error: {str(e)}"
            import traceback
            traceback.print_exc()
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
    # Also include detailed progress if available
    detailed_progress = {}
    if PROGRESS_FILE.exists():
        try:
            progress_tracker = ProgressTracker(PROGRESS_FILE)
            detailed_progress = progress_tracker.get_progress()
        except:
            pass
    
    return jsonify({
        **pipeline_status,
        'detailed_progress': detailed_progress
    })


@app.route('/api/pipeline/progress/<video_id>')
def get_video_progress(video_id: str):
    """Get detailed progress for a specific video"""
    if not PROGRESS_FILE.exists():
        return jsonify({'error': 'No progress data available'}), 404
    
    try:
        progress_tracker = ProgressTracker(PROGRESS_FILE)
        video_progress = progress_tracker.get_progress(video_id)
        
        if not video_progress:
            return jsonify({'error': 'Video not found in progress'}), 404
        
        return jsonify(video_progress)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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


def get_videos_from_playlist(playlist_id: str) -> List[str]:
    """Get video IDs from a YouTube playlist"""
    api_key = config.api.google_api_key or os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        return []
    
    videos = []
    next_page_token = None
    youtube_api_url = "https://www.googleapis.com/youtube/v3"
    max_results = 50
    
    while True:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": max_results,
            "key": api_key
        }
        
        if next_page_token:
            params["pageToken"] = next_page_token
        
        try:
            response = requests.get(f"{youtube_api_url}/playlistItems", params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"Error fetching playlist: {response.status_code}")
                break
            
            data = response.json()
            
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                resource_id = snippet.get("resourceId", {})
                video_id = resource_id.get("videoId")
                if video_id:
                    videos.append(video_id)
            
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
                
        except Exception as e:
            print(f"Error fetching playlist: {e}")
            break
    
    return videos


@app.route('/api/pipeline/add-playlist', methods=['POST'])
def add_playlist_api():
    """Add videos from a YouTube playlist to the processing queue"""
    data = request.get_json()
    
    if not data or 'playlist_id' not in data:
        return jsonify({'error': 'No playlist ID provided'}), 400
    
    playlist_input = data['playlist_id'].strip()
    
    # Extract playlist ID from URL if provided
    playlist_id = None
    if re.match(r'^[a-zA-Z0-9_-]+$', playlist_input):
        # Already a playlist ID
        playlist_id = playlist_input
    else:
        # Try to extract from URL
        # Format: https://www.youtube.com/playlist?list=PLAYLIST_ID
        match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', playlist_input)
        if match:
            playlist_id = match.group(1)
    
    if not playlist_id:
        return jsonify({'error': 'Invalid playlist ID or URL'}), 400
    
    # Fetch videos from playlist
    playlist_videos = get_videos_from_playlist(playlist_id)
    
    if not playlist_videos:
        return jsonify({
            'error': 'No videos found in playlist or API error',
            'playlist_id': playlist_id
        }), 400
    
    # Add videos to the queue (using existing add_video_ids function)
    result = add_video_ids(playlist_videos)
    
    return jsonify({
        'success': True,
        'message': f"Added {result['added']} videos from playlist",
        'playlist_id': playlist_id,
        'playlist_videos_count': len(playlist_videos),
        'added': result['added'],
        'already_existed': len(playlist_videos) - result['added'],
        'new_video_ids': result['new_video_ids'],
        'total_videos': result['total_videos']
    })


@app.route('/partial/video-card/<video_id>')
def partial_video_card(video_id: str):
    """HTMX partial: Video card"""
    video_data = data_loader.get_video_insights(video_id)
    
    if not video_data:
        return "<div>Video not found</div>", 404
    
    return render_template('partials/video_card.html', video_data=video_data)


@app.route('/api/embeddings/generate', methods=['POST'])
def generate_embeddings():
    """Generate embeddings for all transcripts or a specific video"""
    # #region agent log
    try:
        import json as json_module
        import time as time_module
        with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
            f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E10","location":"app.py:1188","message":"generate_embeddings() API endpoint called","data":{"method":request.method,"content_type":request.content_type,"has_json":request.is_json,"has_form":bool(request.form),"form_keys":list(request.form.keys()) if request.form else []},"timestamp":int(time_module.time()*1000)}) + '\n')
    except:
        pass
    # #endregion
    try:
        # HTMX sends form-encoded data, but also support JSON
        # HTMX hx-vals='{"video_id": "xxx"}' becomes form field: video_id=xxx
        if request.is_json:
            data = request.get_json() or {}
        else:
            # Parse form data (HTMX sends hx-vals as form-encoded)
            data = request.form.to_dict()
            # HTMX automatically parses JSON in hx-vals and sends as form fields
            # So if we have video_id in form, use it directly
        
        video_id = data.get('video_id')  # Optional: generate for specific video
        force = data.get('force', False)
        
        # #region agent log
        try:
            import json as json_module
            import time as time_module
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E10","location":"app.py:1215","message":"generate_embeddings() parsed request data","data":{"video_id":video_id,"force":force,"data_keys":list(data.keys()),"transcripts_dir":str(semantic_search.transcripts_dir),"transcripts_dir_exists":semantic_search.transcripts_dir.exists()},"timestamp":int(time_module.time()*1000)}) + '\n')
        except:
            pass
        # #endregion
        
        if video_id:
            # Check if embeddings already exist (unless force is True)
            if not force and video_id in semantic_search.embeddings_cache:
                if request.headers.get('HX-Request'):  # HTMX request - reload repository row
                    # Reload embeddings cache to ensure it's up to date
                    semantic_search._load_embeddings()
                    return _get_repository_row_html(video_id)
                return jsonify({
                    'status': 'success',
                    'message': f'Embeddings already exist for {video_id}',
                    'video_id': video_id
                })
            
            success = semantic_search.generate_embeddings_for_video(video_id, force_regenerate=force)
            
            # #region agent log
            try:
                import json as json_module
                import time as time_module
                with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                    f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E11","location":"app.py:1181","message":"generate_embeddings_for_video() completed","data":{"video_id":video_id,"success":success,"embeddings_file":str(semantic_search.embeddings_file),"cache_has_video":video_id in semantic_search.embeddings_cache},"timestamp":int(time_module.time()*1000)}) + '\n')
            except:
                pass
            # #endregion
            
            if request.headers.get('HX-Request'):  # HTMX request - reload repository row
                if success:
                    # Reload embeddings cache to ensure it's up to date
                    semantic_search._load_embeddings()
                    return _get_repository_row_html(video_id)
                else:
                    return f'<tr><td colspan="6" class="px-6 py-4 text-red-600">Failed to generate embeddings for {video_id}</td></tr>'
            
            return jsonify({
                'status': 'success' if success else 'error',
                'message': f'Embeddings generated for {video_id}' if success else f'Failed to generate embeddings for {video_id}',
                'video_id': video_id
            })
        else:
            results = semantic_search.generate_embeddings_for_all(force_regenerate=force)
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)
            
            if request.headers.get('HX-Request'):  # HTMX request
                status_html = f'<span class="text-green-600">✓ Generated embeddings for {success_count}/{total_count} videos</span>'
                return status_html
            
            return jsonify({
                'status': 'success',
                'message': f'Generated embeddings for {success_count}/{total_count} videos',
                'results': results
            })
    except Exception as e:
        if request.headers.get('HX-Request'):  # HTMX request
            return f'<tr><td colspan="6" class="px-6 py-4 text-red-600">Error: {str(e)}</td></tr>', 500
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _get_repository_row_html(video_id: str) -> str:
    """Helper function to generate repository row HTML for HTMX updates"""
    # Reuse the same logic as the repository route
    insights_dir = config.paths.insights_dir
    transcripts_dir = config.paths.raw_transcripts_dir
    chunks_dir = config.paths.chunks_dir
    audio_dir = config.paths.audio_dir
    
    insight_file = insights_dir / f"{video_id}_insights.json"
    if not insight_file.exists():
        return f'<tr><td colspan="6" class="px-6 py-4 text-gray-500">File not found</td></tr>'
    
    try:
        # Load insight data
        with open(insight_file, 'r', encoding='utf-8') as f:
            insight_data = json.load(f)
        
        file_stat = insight_file.stat()
        insights_count = len(insight_data.get('insights', []))
        nuggets_count = len(insight_data.get('golden_nuggets', []))
        
        # Check for related files
        transcript_file = transcripts_dir / f"{video_id}.txt"
        audio_file = audio_dir / f"{video_id}.mp3"
        chunks_dir_video = chunks_dir / video_id
        
        has_transcript = transcript_file.exists()
        has_audio = audio_file.exists()
        has_chunks = chunks_dir_video.exists() and any(chunks_dir_video.glob("*.mp3"))
        has_embeddings = video_id in semantic_search.embeddings_cache
        
        transcript_size = transcript_file.stat().st_size if has_transcript else 0
        audio_size = audio_file.stat().st_size if has_audio else 0
        chunk_count = len(list(chunks_dir_video.glob("*.mp3"))) if has_chunks else 0
        
        from datetime import datetime
        modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        
        # Generate HTML directly (matching repository.html structure)
        embeddings_badge = ''
        if has_embeddings:
            embeddings_badge = '<span class="inline-flex items-center px-2 py-1 rounded-md bg-green-100 text-green-800 text-xs font-medium">🧠 Embeddings Available</span>'
        elif has_transcript:
            embeddings_badge = '<span class="inline-flex items-center px-2 py-1 rounded-md bg-yellow-100 text-yellow-800 text-xs font-medium">🧠 Embeddings Not Generated</span>'
        else:
            embeddings_badge = '<span class="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-gray-500 text-xs font-medium">🧠 No transcript</span>'
        
        generate_button = ''
        if has_transcript and not has_embeddings:
            generate_button = f'''
                <button 
                    class="text-yellow-600 hover:text-yellow-900 text-xs text-left"
                    hx-post="/api/embeddings/generate"
                    hx-vals='{{"video_id": "{video_id}"}}'
                    hx-target="closest tr"
                    hx-swap="outerHTML"
                    hx-indicator="#loading-{video_id}"
                    id="generate-embeddings-{video_id}"
                >
                    🧠 Generate Embeddings
                </button>
                <div id="loading-{video_id}" class="htmx-indicator text-xs text-gray-500">Generating...</div>
            '''
        
        transcript_badge = f'<span class="inline-flex items-center px-2 py-1 rounded-md bg-green-100 text-green-800 text-xs font-medium">📝 Transcript ({transcript_size / 1024:.1f} KB)</span>' if has_transcript else '<span class="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-gray-500 text-xs font-medium">📝 No transcript</span>'
        audio_badge = f'<span class="inline-flex items-center px-2 py-1 rounded-md bg-purple-100 text-purple-800 text-xs font-medium">🔊 Audio ({audio_size / 1024 / 1024:.1f} MB)</span>' if has_audio else '<span class="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-gray-500 text-xs font-medium">🔊 No audio</span>'
        chunks_badge = f'<span class="inline-flex items-center px-2 py-1 rounded-md bg-indigo-100 text-indigo-800 text-xs font-medium">✂️ {chunk_count} chunks</span>' if has_chunks else '<span class="inline-flex items-center px-2 py-1 rounded-md bg-gray-100 text-gray-500 text-xs font-medium">✂️ No chunks</span>'
        
        return f'''
    <tr class="hover:bg-gray-50">
        <td class="px-6 py-4 whitespace-nowrap">
            <div class="flex items-center">
                <span class="text-lg mr-2">📄</span>
                <div>
                    <div class="text-sm font-medium text-gray-900">
                        <a href="/video/{video_id}" class="text-blue-600 hover:text-blue-800" hx-get="/video/{video_id}" hx-target="body" hx-push-url="true">{video_id}</a>
                    </div>
                    <div class="text-xs text-gray-500 font-mono">{video_id}_insights.json</div>
                </div>
            </div>
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
            <div class="text-sm text-gray-900">
                <span class="inline-flex items-center px-2 py-1 rounded-md bg-blue-100 text-blue-800 text-xs font-medium mr-1">💡 {insights_count}</span>
                <span class="inline-flex items-center px-2 py-1 rounded-md bg-yellow-100 text-yellow-800 text-xs font-medium">⭐ {nuggets_count}</span>
            </div>
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
            <div class="flex flex-col gap-1">
                {transcript_badge}
                {audio_badge}
                {chunks_badge}
                {embeddings_badge}
            </div>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{file_stat.st_size / 1024:.1f} KB</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{modified}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
            <div class="flex flex-col gap-2">
                <a href="/video/{video_id}" class="text-blue-600 hover:text-blue-900" hx-get="/video/{video_id}" hx-target="body" hx-push-url="true">View Video →</a>
                <a href="/insight-file/{video_id}" class="text-green-600 hover:text-green-900 text-xs" target="_blank">📄 View JSON</a>
                <a href="/api/insight-file/{video_id}" class="text-purple-600 hover:text-purple-900 text-xs" download="{video_id}_insights.json">⬇️ Download</a>
                {generate_button}
            </div>
        </td>
    </tr>
    '''
    except Exception as e:
        return f'<tr><td colspan="6" class="px-6 py-4 text-red-600">Error: {str(e)}</td></tr>'


@app.route('/api/embeddings/status')
def embeddings_status():
    """Get status of embeddings"""
    try:
        video_ids = list(semantic_search.embeddings_cache.keys())
        return jsonify({
            'status': 'success',
            'total_embeddings': len(video_ids),
            'video_ids': video_ids
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting YC Insight Extractor Web Interface")
    print(f"📁 Insights directory: {config.paths.insights_dir}")
    print(f"🌐 Server running at http://localhost:5012")
    print("Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5012)
