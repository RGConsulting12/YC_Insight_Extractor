# YouTube Video Processing Pipeline

This pipeline downloads YouTube videos, transcribes them, and extracts insights using AI.

## Overview

The pipeline consists of the following steps:

1. **Download Audio** - Extract audio from YouTube videos using yt-dlp
2. **Split Audio** - Split long audio files into manageable chunks
3. **Transcribe** - Convert audio chunks to text using OpenAI Whisper
4. **Assemble** - Combine transcript chunks into a complete transcript
5. **Extract Insights** - Use LLM to extract key insights from the transcript

## Prerequisites

### System Dependencies

- **ffmpeg** - For audio processing
- **yt-dlp** - For downloading YouTube videos

### Python Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root with your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Quick Start

1. **Test the pipeline** (recommended first):
   ```bash
   cd src/transcript
   python test_pipeline.py
   ```

2. **Run the full pipeline** on all videos:
   ```bash
   python pipeline.py
   ```

3. **Process specific videos**:
   ```bash
   python pipeline.py --video-ids VIDEO_ID1 VIDEO_ID2
   ```

4. **Force re-download** of audio files:
   ```bash
   python pipeline.py --force-redownload
   ```

### Individual Components

You can also run individual components:

- **Download audio only**:
  ```bash
  python download_audio.py
  ```

- **Split audio into chunks**:
  ```bash
  python split_audio.py
  ```

- **Transcribe chunks**:
  ```bash
  python transcribe_chunks.py
  ```

- **Assemble transcripts**:
  ```bash
  python assemble_transcripts.py
  ```

- **Extract insights**:
  ```bash
  python extact_insights.py
  ```

## Output Structure

The pipeline creates the following directory structure:

```
data/
├── audio/                    # Downloaded audio files
├── audio_chunks/            # Split audio chunks
├── raw_transcripts/         # Complete transcripts
└── insights/               # Extracted insights
    ├── video_id_insights.json
    └── pipeline_summary.json
```

## Configuration

### Video IDs

The pipeline reads video IDs from `src/scraper/data/video_ids.json`. This file should contain a list of YouTube video IDs:

```json
[
  "p8Jx4qvDoSo",
  "a8-QsBHoH94",
  "2Yguz5U-Nic",
  "2jOnoTEk-xA",
  "RNJCfif1dPY",
  "5QcCeSsNRks",
  "_PioN-CpOP0",
  "AUUZuzVHKdo",
  "V979Wd1gmTU",
  "cFIlta1GkiE",
  "LCEmiRjPEtQ"
]
```

### Audio Processing

- **Chunk duration**: 20 minutes (1200 seconds) by default
- **Overlap**: 3 minutes (200 seconds) between chunks
- **Audio format**: MP3
- **Quality**: Best available

### Transcription

- **Model**: OpenAI Whisper (gpt-4o-transcribe)
- **Language**: Auto-detected
- **Chunk processing**: Sequential to maintain order

### Insight Extraction

- **Model**: GPT-4o
- **Temperature**: 0.3 (balanced creativity and consistency)
- **Output format**: JSON with summary, insights, and golden nuggets

## Troubleshooting

### Common Issues

1. **yt-dlp not found**:
   ```bash
   pip install yt-dlp
   ```

2. **ffmpeg not found**:
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt install ffmpeg`
   - Windows: Download from https://ffmpeg.org/

3. **OpenAI API key not set**:
   - Create `.env` file with `OPENAI_API_KEY=your_key`

4. **Audio download fails**:
   - Check internet connection
   - Verify video ID is valid
   - Try with `--force-redownload` flag

### Error Logs

- Transcription errors are logged to `transcription_errors.log`
- Pipeline summary is saved to `data/insights/pipeline_summary.json`

## Performance Tips

1. **Batch processing**: Process multiple videos in sequence
2. **Resume capability**: Pipeline skips already processed files
3. **Parallel processing**: Consider running multiple instances for different videos
4. **Storage**: Ensure sufficient disk space for audio files

## Customization

### Modify Insight Extraction

Edit the prompt in `extact_insights.py`:

```python
INSIGHT_PROMPT = """
Your custom prompt here...
"""
```

### Change Audio Chunk Size

Modify `split_audio.py`:

```python
def split_by_length(audio_path, base_name, output_dir, chunk_duration=1800):  # 30 minutes
```

### Use Different Transcription Model

Update `transcribe_chunks.py`:

```python
response = client.audio.transcriptions.create(
    model="whisper-1",  # Different model
    file=f
)
```

## License

This project is for educational and research purposes. Please respect YouTube's terms of service and OpenAI's usage policies.

## 📍 **Storage Locations & Data Flow**

### **1. Audio Chunks Storage** 📁
**Location**: `src/transcript/data/audio_chunks/{video_id}/`

**Example for video `p8Jx4qvDoSo`:**
```
src/transcript/data/audio_chunks/p8Jx4qvDoSo/
├── p8Jx4qvDoSo_chunk_0.mp3  (0-20 minutes)
├── p8Jx4qvDoSo_chunk_1.mp3  (17-37 minutes) 
└── p8Jx4qvDoSo_chunk_2.mp3  (34-54 minutes)
```

**Chunk Configuration:**
- **Duration**: 20 minutes (1200 seconds) per chunk
- **Overlap**: 3 minutes (200 seconds) between chunks
- **Format**: MP3 files
- **Size**: ~10-50MB per chunk

### **2. Chunk Assembly for LLM** 🔗
**YES, chunks are joined together** before the LLM API call!

**Process:**
1. **Individual transcription**: Each audio chunk → OpenAI Whisper → Text
2. **In-memory assembly**: All transcript chunks are combined into a single string
3. **Single LLM call**: The complete assembled transcript is sent to GPT-4o for insight extraction

**Assembly format:**
```
=== chunk_0 ===
[transcript of first 20 minutes]

=== chunk_1 ===
[transcript of next 20 minutes]

=== chunk_2 ===
[transcript of final portion]
```

### **3. Insights Storage** 🧠
**Location**: `data/insights/`

**Files created:**
```
data/insights/
├── p8Jx4qvDoSo_insights.json      # Individual video insights
├── a8-QsBHoH94_insights.json      # Individual video insights
├── 2Yguz5U-Nic_insights.json      # Individual video insights
└── pipeline_summary.json          # Overall pipeline results
```

**Insights JSON structure:**
```json
{
  "summary": "Main points of the presentation...",
  "insights": ["Key insight 1", "Key insight 2"],
  "golden_nuggets": ["Memorable quote 1", "Breakthrough idea 2"],
  "video_id": "p8Jx4qvDoSo"
}
```

## 🔄 **Complete Data Flow**

```
YouTube Video ID
       ↓
📥 Download Audio → src/transcript/data/audio/{video_id}.mp3
       ↓
✂️ Split into Chunks → src/transcript/data/audio_chunks/{video_id}/
       ↓
 Transcribe Each Chunk → [In-memory transcript strings]
       ↓
📝 Assemble Transcript → src/transcript/data/raw_transcripts/{video_id}.txt
       ↓
 Extract Insights → data/insights/{video_id}_insights.json
```