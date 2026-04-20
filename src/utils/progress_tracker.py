"""
Progress tracking for video processing pipeline
Tracks detailed progress for each video and stage
"""
import json
import time
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class ProgressTracker:
    """Track progress for video processing"""
    
    # Processing stages
    STAGES = {
        'queued': {'name': 'Queued', 'progress': 0},
        'downloading': {'name': 'Downloading Audio', 'progress': 10},
        'chunking': {'name': 'Splitting into Chunks', 'progress': 25},
        'transcribing': {'name': 'Transcribing Audio', 'progress': 50},
        'assembling': {'name': 'Assembling Transcript', 'progress': 75},
        'extracting': {'name': 'Extracting Insights', 'progress': 90},
        'completed': {'name': 'Completed', 'progress': 100},
        'failed': {'name': 'Failed', 'progress': 0}
    }
    
    def __init__(self, progress_file: Path):
        """
        Initialize progress tracker
        
        Args:
            progress_file: Path to JSON file for storing progress
        """
        self.progress_file = progress_file
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        self._progress = self._load()
    
    def _load(self) -> Dict:
        """Load progress from file"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'videos': {},
            'last_updated': None,
            'current_video': None,
            'total_videos': 0,
            'processed': 0
        }
    
    def _save(self):
        """Save progress to file"""
        # #region agent log
        try:
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"progress_tracker.py:56","message":"_save() called","data":{"progress_file":str(self.progress_file),"file_exists":self.progress_file.exists(),"videos_count":len(self._progress.get('videos',{}))},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except:
            pass
        # #endregion
        self._progress['last_updated'] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self._progress, f, indent=2, ensure_ascii=False)
            # #region agent log
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                file_stat = self.progress_file.stat()
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"progress_tracker.py:60","message":"_save() completed","data":{"progress_file":str(self.progress_file),"file_size":file_stat.st_size,"file_written":True},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            # #endregion
        except Exception as e:
            # #region agent log
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                import traceback
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"progress_tracker.py:62","message":"_save() failed","data":{"progress_file":str(self.progress_file),"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            # #endregion
            raise
    
    def start_processing(self, video_ids: list):
        """Initialize progress tracking for a batch of videos"""
        self._progress = {
            'videos': {},
            'last_updated': datetime.now().isoformat(),
            'current_video': None,
            'total_videos': len(video_ids),
            'processed': 0,
            'started_at': datetime.now().isoformat()
        }
        
        for video_id in video_ids:
            self._progress['videos'][video_id] = {
                'video_id': video_id,
                'stage': 'queued',
                'stage_name': self.STAGES['queued']['name'],
                'progress': 0,
                'message': 'Waiting to start...',
                'started_at': None,
                'completed_at': None,
                'errors': []
            }
        
        self._save()
    
    def update_stage(self, video_id: str, stage: str, message: str = None, error: str = None):
        """
        Update processing stage for a video
        
        Args:
            video_id: Video ID
            stage: Stage name (one of STAGES keys)
            message: Optional status message
            error: Optional error message
        """
        # #region agent log
        try:
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"progress_tracker.py:85","message":"update_stage() called","data":{"video_id":video_id,"stage":stage,"message":message,"progress_file":str(self.progress_file)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except:
            pass
        # #endregion
        if video_id not in self._progress['videos']:
            self._progress['videos'][video_id] = {
                'video_id': video_id,
                'stage': 'queued',
                'stage_name': self.STAGES['queued']['name'],
                'progress': 0,
                'message': 'Waiting to start...',
                'started_at': None,
                'completed_at': None,
                'errors': []
            }
        
        video_progress = self._progress['videos'][video_id]
        
        if stage in self.STAGES:
            video_progress['stage'] = stage
            video_progress['stage_name'] = self.STAGES[stage]['name']
            video_progress['progress'] = self.STAGES[stage]['progress']
        
        if message:
            video_progress['message'] = message
        
        if error:
            video_progress['errors'].append(error)
            video_progress['stage'] = 'failed'
            video_progress['stage_name'] = self.STAGES['failed']['name']
        
        if video_progress['started_at'] is None and stage != 'queued':
            video_progress['started_at'] = datetime.now().isoformat()
        
        if stage in ['completed', 'failed']:
            video_progress['completed_at'] = datetime.now().isoformat()
            self._progress['processed'] = len([v for v in self._progress['videos'].values() 
                                               if v['stage'] in ['completed', 'failed']])
        
        self._progress['current_video'] = video_id
        self._progress['last_updated'] = datetime.now().isoformat()
        # #region agent log
        try:
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"progress_tracker.py:127","message":"About to call _save() from update_stage","data":{"video_id":video_id,"stage":stage,"progress_file":str(self.progress_file)},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except:
            pass
        # #endregion
        self._save()
        # #region agent log
        try:
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                import json as json_module
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"progress_tracker.py:130","message":"_save() completed in update_stage","data":{"video_id":video_id,"stage":stage,"file_exists":self.progress_file.exists()},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except:
            pass
        # #endregion
    
    def update_transcription_progress(self, video_id: str, current_chunk: int, total_chunks: int):
        """Update progress during transcription (chunk-by-chunk)"""
        if video_id not in self._progress['videos']:
            return
        
        # Transcription is stage 3, progress from 25% to 75%
        base_progress = 25
        transcription_range = 50  # 25% to 75%
        chunk_progress = (current_chunk / total_chunks) * transcription_range
        
        video_progress = self._progress['videos'][video_id]
        video_progress['progress'] = base_progress + chunk_progress
        video_progress['message'] = f"Transcribing chunk {current_chunk}/{total_chunks}"
        self._progress['last_updated'] = datetime.now().isoformat()
        self._save()
    
    def get_progress(self, video_id: Optional[str] = None) -> Dict:
        """
        Get progress for a specific video or all videos
        
        Args:
            video_id: Optional video ID to get progress for
        
        Returns:
            Progress dictionary
        """
        if video_id:
            return self._progress['videos'].get(video_id, {})
        return self._progress
    
    def clear(self):
        """Clear all progress"""
        self._progress = {
            'videos': {},
            'last_updated': None,
            'current_video': None,
            'total_videos': 0,
            'processed': 0
        }
        self._save()
