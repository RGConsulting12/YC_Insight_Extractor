# Usage Examples

## Configuration Management

### Basic Usage

```python
from src.config import get_config

# Get default configuration
config = get_config()

# Access paths
audio_path = config.paths.audio_dir / "video_id.mp3"
insights_path = config.paths.insights_dir / "video_id_insights.json"

# Access API settings
openai_key = config.api.openai_api_key
model = config.api.insight_model

# Access processing settings
chunk_duration = config.processing.chunk_duration
```

### Custom Configuration

```python
from src.config import Config, PathsConfig, ProcessingConfig, APIConfig
from pathlib import Path

# Create custom configuration
custom_paths = PathsConfig(
    project_root=Path("/custom/path"),
    audio_dir=Path("/custom/path/audio"),
    # ... other paths
)

config = Config(
    paths=custom_paths,
    processing=ProcessingConfig(chunk_duration=1800),  # 30 minutes
    api=APIConfig(temperature=0.5)
)
```

## Logging

### Basic Logging

```python
from src.utils import setup_logger
from pathlib import Path

# Setup logger
logger = setup_logger(__name__)

# Use logger
logger.info("Processing video")
logger.error("Failed to download")
logger.debug("Debug information")
```

### File Logging

```python
from src.utils import setup_logger, get_log_file_path
from src.config import get_config

config = get_config()
log_file = get_log_file_path(config.paths.project_root, "pipeline")

logger = setup_logger(__name__, log_file=log_file)
logger.info("This will be logged to both console and file")
```

### Using LoggerMixin

```python
from src.utils import LoggerMixin

class VideoProcessor(LoggerMixin):
    def process(self, video_id: str):
        self.logger.info(f"Processing {video_id}")
        try:
            # Process video
            self.logger.info("Success")
        except Exception as e:
            self.logger.error(f"Error: {e}")
```

## Cost Tracking

### Basic Cost Tracking

```python
from src.utils import CostTracker
from pathlib import Path

# Initialize tracker
tracker = CostTracker(cost_file=Path("costs.json"))

# Track Whisper cost
tracker.track_whisper_cost(
    duration_minutes=45.5,
    video_id="p8Jx4qvDoSo"
)

# Track GPT cost
tracker.track_gpt_cost(
    input_tokens=50000,
    output_tokens=2000,
    video_id="p8Jx4qvDoSo"
)

# Get summary
summary = tracker.get_summary()
print(f"Total cost: ${summary['total_cost']:.2f}")
print(f"By service: {summary['by_service']}")
```

### Cost Estimation

```python
from src.utils import CostTracker

tracker = CostTracker()

# Estimate cost before processing
estimate = tracker.estimate_video_cost(
    duration_minutes=40,
    transcript_length_chars=50000
)

print(f"Estimated Whisper cost: ${estimate['whisper_cost']:.2f}")
print(f"Estimated GPT cost: ${estimate['gpt_cost']:.2f}")
print(f"Total estimated cost: ${estimate['total_cost']:.2f}")
```

## Integration Example

### Updated Pipeline with New Utilities

```python
from src.config import get_config
from src.utils import setup_logger, get_log_file_path, CostTracker
from pathlib import Path

# Setup
config = get_config()
config.validate()

log_file = get_log_file_path(config.paths.project_root)
logger = setup_logger(__name__, log_file=log_file)

cost_tracker = CostTracker(
    cost_file=config.paths.project_root / "data" / "costs.json"
)

# Process video
video_id = "p8Jx4qvDoSo"
logger.info(f"Starting processing for {video_id}")

# Download audio
# ... download logic ...

# Transcribe
# ... transcription logic ...
duration_minutes = 40.8
cost_tracker.track_whisper_cost(duration_minutes, video_id=video_id)

# Extract insights
# ... insight extraction logic ...
cost_tracker.track_gpt_cost(
    input_tokens=50000,
    output_tokens=2000,
    video_id=video_id
)

# Summary
summary = cost_tracker.get_summary()
logger.info(f"Processing complete. Total cost: ${summary['total_cost']:.2f}")
```

## Migration Guide

### Updating Existing Code

**Before:**
```python
AUDIO_DIR = "data/audio"
INSIGHTS_DIR = "data/insights"
```

**After:**
```python
from src.config import get_config

config = get_config()
audio_dir = config.paths.audio_dir
insights_dir = config.paths.insights_dir
```

**Before:**
```python
print(f"Processing video: {video_id}")
```

**After:**
```python
from src.utils import setup_logger

logger = setup_logger(__name__)
logger.info(f"Processing video: {video_id}")
```

