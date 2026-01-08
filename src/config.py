"""
Configuration management for YC Insight Extractor
Centralizes all configuration settings and paths
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class PathsConfig:
    """Configuration for file paths"""
    project_root: Path
    audio_dir: Path
    chunks_dir: Path
    transcripts_dir: Path
    raw_transcripts_dir: Path
    chunk_transcripts_dir: Path
    insights_dir: Path
    metadata_dir: Path
    video_ids_path: Path
    
    def __post_init__(self):
        """Create directories if they don't exist"""
        for path in [
            self.audio_dir,
            self.chunks_dir,
            self.transcripts_dir,
            self.raw_transcripts_dir,
            self.chunk_transcripts_dir,
            self.insights_dir,
            self.metadata_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class ProcessingConfig:
    """Configuration for processing parameters"""
    chunk_duration: int = 1200  # seconds (20 minutes)
    chunk_overlap: int = 200     # seconds (3.3 minutes)
    max_workers: int = 5         # for parallel processing
    force_redownload: bool = False


@dataclass
class APIConfig:
    """Configuration for API settings"""
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    whisper_model: str = "gpt-4o-transcribe"
    insight_model: str = "gpt-4o"
    temperature: float = 0.3
    max_retries: int = 3
    api_delay: float = 0.2  # seconds between API calls
    
    def __post_init__(self):
        """Load API keys from environment if not provided"""
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.google_api_key:
            self.google_api_key = os.getenv("GOOGLE_API_KEY")


@dataclass
class CostConfig:
    """Configuration for cost tracking"""
    whisper_cost_per_minute: float = 0.006  # $0.006 per minute
    gpt4o_input_cost_per_1k_tokens: float = 2.50  # $2.50 per 1M tokens
    gpt4o_output_cost_per_1k_tokens: float = 10.00  # $10.00 per 1M tokens
    track_costs: bool = True


@dataclass
class Config:
    """Main configuration class combining all configs"""
    paths: PathsConfig
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    api: APIConfig = field(default_factory=APIConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    
    @classmethod
    def from_project_root(cls, project_root: Optional[Path] = None) -> "Config":
        """
        Create configuration from project root
        
        Args:
            project_root: Path to project root. If None, auto-detects from this file.
        
        Returns:
            Config instance
        """
        if project_root is None:
            # Auto-detect project root (2 levels up from src/config.py)
            # src/config.py -> src/ -> yc-insight-extractor/
            project_root = Path(__file__).parent.parent
        
        project_root = Path(project_root)
        
        # Define paths
        paths = PathsConfig(
            project_root=project_root,
            audio_dir=project_root / "src" / "transcript" / "data" / "audio",
            chunks_dir=project_root / "src" / "transcript" / "data" / "audio_chunks",
            transcripts_dir=project_root / "src" / "transcript" / "data" / "transcripts",
            raw_transcripts_dir=project_root / "src" / "transcript" / "data" / "raw_transcripts",
            chunk_transcripts_dir=project_root / "src" / "transcript" / "data" / "chunk_transcripts",
            insights_dir=project_root / "src" / "transcript" / "data" / "insights",
            metadata_dir=project_root / "src" / "scraper" / "data" / "metadata",
            video_ids_path=project_root / "src" / "scraper" / "data" / "video_ids.json",
        )
        
        return cls(
            paths=paths,
            processing=ProcessingConfig(),
            api=APIConfig(),
            cost=CostConfig(),
        )
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        if not self.api.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment or config")
        
        if not self.paths.video_ids_path.exists():
            raise FileNotFoundError(
                f"Video IDs file not found: {self.paths.video_ids_path}"
            )
        
        return True


# Global config instance (can be overridden)
_config: Optional[Config] = None


def get_config(project_root: Optional[Path] = None) -> Config:
    """
    Get global configuration instance
    
    Args:
        project_root: Optional project root path
    
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config.from_project_root(project_root)
    return _config


def set_config(config: Config) -> None:
    """
    Set global configuration instance
    
    Args:
        config: Config instance to use
    """
    global _config
    _config = config

