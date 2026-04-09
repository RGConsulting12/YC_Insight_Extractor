# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

YC Insight Extractor — a CLI Python data pipeline that downloads YouTube video audio, transcribes via OpenAI Whisper API, and extracts business insights with GPT-4o. No web server, no database, no Docker. See `src/transcript/README.md` for full pipeline docs.

### Running the pipeline

- Entry point: `python3 src/transcript/pipeline.py` (from repo root)
- Smoke test: `cd src/transcript && python3 test_pipeline.py`
- Process a single video: `python3 src/transcript/pipeline.py --video-ids VIDEO_ID`

### Environment variables

A `.env` file in the repo root (or exported env vars) is required:

- `OPENAI_API_KEY` — **required** for transcription and insight extraction
- `YOUTUBE_API_KEY` — optional; pre-scraped data exists in `src/scraper/data/`

### Gotchas

- **`openai-whisper` in `requirements.txt`**: This package is listed but **never imported**. The codebase uses the OpenAI API (`gpt-4o-transcribe` model) for transcription, not the local Whisper model. Installing `openai-whisper` fails on Python 3.12 due to a `pkg_resources` / `setuptools` compatibility issue. Install the other dependencies individually or skip `openai-whisper`.
- **`httpx` compatibility**: `openai==1.51.0` requires `httpx<0.28`. If pip resolves `httpx>=0.28`, the OpenAI client will crash with `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`. Fix: `pip install 'httpx<0.28'`.
- **YouTube downloads in CI/cloud**: `yt-dlp` audio downloads may fail in restricted network environments. The dependency check in `test_pipeline.py` will pass, but the download step will fail. This is an environment limitation, not a code bug.
- **Hardcoded macOS paths**: `src/scraper/get_video_links.py` and `src/scraper/get_video_metadata.py` have hardcoded `/Users/garcia/...` paths for `.env` loading. These scripts are optional since scraped data is already committed.
- **No `python` alias**: The VM only has `python3`; use `python3` to run scripts.
- **Lint**: No linter configured in the repo. Use `python3 -m py_compile <file>` for syntax checks.
