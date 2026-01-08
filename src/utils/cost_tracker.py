"""
Cost tracking utilities for API usage
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import json
from pathlib import Path


@dataclass
class CostEntry:
    """Single cost entry"""
    timestamp: datetime
    service: str  # 'whisper' or 'gpt'
    operation: str  # e.g., 'transcription', 'insight_extraction'
    cost: float
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "service": self.service,
            "operation": self.operation,
            "cost": self.cost,
            "metadata": self.metadata
        }


class CostTracker:
    """Track API costs across the pipeline"""
    
    def __init__(self, cost_file: Optional[Path] = None):
        """
        Initialize cost tracker
        
        Args:
            cost_file: Path to cost tracking file (JSON)
        """
        self.cost_file = cost_file
        self.entries: list[CostEntry] = []
        self._load_existing()
    
    def _load_existing(self):
        """Load existing cost entries from file"""
        if self.cost_file and self.cost_file.exists():
            try:
                with open(self.cost_file, 'r') as f:
                    data = json.load(f)
                    for entry_data in data.get('entries', []):
                        entry = CostEntry(
                            timestamp=datetime.fromisoformat(entry_data['timestamp']),
                            service=entry_data['service'],
                            operation=entry_data['operation'],
                            cost=entry_data['cost'],
                            metadata=entry_data.get('metadata', {})
                        )
                        self.entries.append(entry)
            except Exception as e:
                print(f"Warning: Could not load cost history: {e}")
    
    def track_whisper_cost(
        self,
        duration_minutes: float,
        cost_per_minute: float = 0.006,
        video_id: Optional[str] = None
    ):
        """
        Track Whisper API cost
        
        Args:
            duration_minutes: Audio duration in minutes
            cost_per_minute: Cost per minute (default: $0.006)
            video_id: Optional video ID for tracking
        """
        cost = duration_minutes * cost_per_minute
        entry = CostEntry(
            timestamp=datetime.now(),
            service="whisper",
            operation="transcription",
            cost=cost,
            metadata={
                "duration_minutes": duration_minutes,
                "cost_per_minute": cost_per_minute,
                "video_id": video_id
            }
        )
        self.entries.append(entry)
        self._save()
    
    def track_gpt_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4o",
        input_cost_per_1k: float = 2.50,
        output_cost_per_1k: float = 10.00,
        video_id: Optional[str] = None,
        operation: str = "insight_extraction"
    ):
        """
        Track GPT API cost
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            input_cost_per_1k: Cost per 1K input tokens (in dollars per 1M tokens)
            output_cost_per_1k: Cost per 1K output tokens (in dollars per 1M tokens)
            video_id: Optional video ID for tracking
            operation: Operation type
        """
        # Convert to cost per 1M tokens
        input_cost = (input_tokens / 1_000_000) * (input_cost_per_1k * 1000)
        output_cost = (output_tokens / 1_000_000) * (output_cost_per_1k * 1000)
        total_cost = input_cost + output_cost
        
        entry = CostEntry(
            timestamp=datetime.now(),
            service="gpt",
            operation=operation,
            cost=total_cost,
            metadata={
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "video_id": video_id
            }
        )
        self.entries.append(entry)
        self._save()
    
    def get_total_cost(self) -> float:
        """Get total cost across all entries"""
        return sum(entry.cost for entry in self.entries)
    
    def get_cost_by_service(self) -> Dict[str, float]:
        """Get cost breakdown by service"""
        breakdown = {}
        for entry in self.entries:
            breakdown[entry.service] = breakdown.get(entry.service, 0) + entry.cost
        return breakdown
    
    def get_cost_by_video(self) -> Dict[str, float]:
        """Get cost breakdown by video ID"""
        breakdown = {}
        for entry in self.entries:
            video_id = entry.metadata.get('video_id', 'unknown')
            breakdown[video_id] = breakdown.get(video_id, 0) + entry.cost
        return breakdown
    
    def get_summary(self) -> Dict:
        """Get cost summary"""
        return {
            "total_cost": self.get_total_cost(),
            "by_service": self.get_cost_by_service(),
            "by_video": self.get_cost_by_video(),
            "entry_count": len(self.entries)
        }
    
    def _save(self):
        """Save cost entries to file"""
        if self.cost_file:
            self.cost_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "entries": [entry.to_dict() for entry in self.entries],
                "summary": self.get_summary()
            }
            with open(self.cost_file, 'w') as f:
                json.dump(data, f, indent=2)
    
    def estimate_video_cost(
        self,
        duration_minutes: float,
        transcript_length_chars: int,
        whisper_cost_per_minute: float = 0.006,
        gpt_input_cost_per_1k: float = 2.50,
        gpt_output_cost_per_1k: float = 10.00
    ) -> Dict[str, float]:
        """
        Estimate cost for processing a video
        
        Args:
            duration_minutes: Video duration in minutes
            transcript_length_chars: Estimated transcript length in characters
            whisper_cost_per_minute: Whisper cost per minute
            gpt_input_cost_per_1k: GPT input cost per 1K tokens
            gpt_output_cost_per_1k: GPT output cost per 1K tokens
        
        Returns:
            Dictionary with cost breakdown
        """
        whisper_cost = duration_minutes * whisper_cost_per_minute
        
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = transcript_length_chars / 4
        # Assume 5x input tokens for context, 0.1x output tokens
        input_tokens = estimated_tokens * 5
        output_tokens = estimated_tokens * 0.1
        
        gpt_input_cost = (input_tokens / 1_000_000) * (gpt_input_cost_per_1k * 1000)
        gpt_output_cost = (output_tokens / 1_000_000) * (gpt_output_cost_per_1k * 1000)
        gpt_cost = gpt_input_cost + gpt_output_cost
        
        return {
            "whisper_cost": whisper_cost,
            "gpt_cost": gpt_cost,
            "total_cost": whisper_cost + gpt_cost,
            "estimated_tokens": estimated_tokens
        }

