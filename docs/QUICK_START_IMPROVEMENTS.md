# Quick Start: Implementing Improvements

This guide provides a quick reference for implementing the recommended improvements.

## 🚀 Immediate Next Steps

### 1. Start Using New Utilities (5 minutes)

The following utilities are ready to use:

#### Configuration
```python
from src.config import get_config

config = get_config()
# Now use config.paths.audio_dir instead of hardcoded paths
```

#### Logging
```python
from src.utils import setup_logger

logger = setup_logger(__name__)
logger.info("Replace print() with logger.info()")
```

#### Cost Tracking
```python
from src.utils import CostTracker

tracker = CostTracker()
tracker.track_whisper_cost(duration_minutes=40, video_id="xyz")
```

### 2. Update Existing Code (30 minutes)

**Priority files to update:**
1. `src/transcript/pipeline.py` - Use config and logger
2. `src/transcript/extract_insights.py` - Add cost tracking
3. `src/transcript/transcribe_chunks.py` - Use logger

**Example migration:**
```python
# OLD
AUDIO_DIR = "data/audio"
print(f"Processing {video_id}")

# NEW
from src.config import get_config
from src.utils import setup_logger

config = get_config()
logger = setup_logger(__name__)
logger.info(f"Processing {video_id}")
```

### 3. Add Enhanced Insight Schema (1 hour)

Update `extract_insights.py` to use the enhanced schema from `IMPROVEMENTS_AND_EXTENSIONS.md`:

```python
INSIGHT_PROMPT = """
Extract structured insights with:
- summary (overview, key_themes, target_audience)
- insights (with type, timestamp, confidence)
- golden_nuggets (with quote, timestamp, context)
- topics (with name, mentions, time_ranges)
- action_items
- q_and_a
...
"""
```

## 📋 Implementation Checklist

### Phase 1: Foundation (Week 1)
- [x] Configuration management (`src/config.py`)
- [x] Logging system (`src/utils/logger.py`)
- [x] Cost tracking (`src/utils/cost_tracker.py`)
- [ ] Update pipeline.py to use config
- [ ] Update all modules to use logger
- [ ] Add cost tracking to API calls
- [ ] Add type hints to key functions
- [ ] Create basic tests

### Phase 2: Core Features (Week 2)
- [ ] Enhanced insight extraction schema
- [ ] Database integration (SQLite)
- [ ] Parallel processing for transcription
- [ ] Chapter-based processing improvements
- [ ] Export formats (Markdown, JSON, CSV)

### Phase 3: Advanced Features (Week 3-4)
- [ ] Vector search for insights
- [ ] Cross-video analysis
- [ ] CLI improvements
- [ ] API server (optional)
- [ ] Web interface (optional)

## 🎯 Quick Wins (Do These First)

1. **Replace print() with logger** (15 min)
   - Find all `print()` statements
   - Replace with `logger.info()`, `logger.error()`, etc.

2. **Use config for paths** (20 min)
   - Replace hardcoded paths with `config.paths.*`

3. **Add cost tracking** (30 min)
   - Track Whisper costs after transcription
   - Track GPT costs after insight extraction
   - Display cost summary at end

4. **Add type hints** (1 hour)
   - Start with function signatures
   - Use `typing` module for complex types

## 📚 Files Created

1. **`docs/IMPROVEMENTS_AND_EXTENSIONS.md`** - Comprehensive improvement guide
2. **`src/config.py`** - Configuration management
3. **`src/utils/logger.py`** - Logging utilities
4. **`src/utils/cost_tracker.py`** - Cost tracking
5. **`docs/USAGE_EXAMPLES.md`** - Usage examples
6. **`docs/QUICK_START_IMPROVEMENTS.md`** - This file

## 🔗 Related Documentation

- `IMPROVEMENTS_AND_EXTENSIONS.md` - Full improvement guide
- `USAGE_EXAMPLES.md` - Code examples
- `SYSTEM_ARCHITECTURE.md` - Current architecture
- `PRODUCT_REQUIREMENTS.md` - Product requirements

## 💡 Tips

1. **Start small**: Don't try to implement everything at once
2. **Test incrementally**: Test each change before moving to the next
3. **Use git**: Commit after each working improvement
4. **Document**: Update docs as you make changes
5. **Ask for help**: Review code with others

## 🐛 Common Issues

### Import Errors
If you get import errors, make sure you're running from the project root:
```bash
cd /path/to/yc-insight-extractor
python -m src.transcript.pipeline
```

### Missing Dependencies
Add any new dependencies to `requirements.txt`:
```bash
pip install new-package
pip freeze > requirements.txt
```

### Path Issues
Always use `pathlib.Path` and the config system:
```python
# Good
from pathlib import Path
audio_path = config.paths.audio_dir / f"{video_id}.mp3"

# Bad
audio_path = f"data/audio/{video_id}.mp3"
```

## 📞 Next Steps

1. Review `IMPROVEMENTS_AND_EXTENSIONS.md` for full details
2. Start with Phase 1 improvements
3. Test thoroughly
4. Move to Phase 2 when Phase 1 is complete

Good luck! 🚀

