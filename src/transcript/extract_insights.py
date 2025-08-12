import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create OpenAI client using the loaded API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Fix these directory paths
TRANSCRIPTS_DIR = "data/raw_transcripts"  # Changed from "data/chunk_transcripts"
INSIGHTS_DIR = "data/insights"             # Changed from "data/chunk_insights"
os.makedirs(INSIGHTS_DIR, exist_ok=True)

INSIGHT_PROMPT = """
You are an expert summarizer and insight extractor.

Given the following transcript, do the following:
1. Summarize the main point of the excerpt in 1–3 sentences.
2. Extract any key insights or original thoughts presented by the speaker.
3. Identify any golden nuggets of knowledge — powerful statements, memorable quotes, or breakthrough ideas.

IMPORTANT: Return ONLY a valid JSON object with exactly these fields:
- "summary" (string): A 1-3 sentence summary
- "insights" (array of strings): List of key insights
- "golden_nuggets" (array of strings): List of memorable quotes or breakthrough ideas

Example format:
{
  "summary": "The presentation covers startup fundamentals focusing on customer development and execution.",
  "insights": ["Startups solve real problems", "Customer development is crucial"],
  "golden_nuggets": ["Ideas are cheap, execution is everything"]
}

Transcript:
"""  # This prompt can be tuned further.

def extract_insights_from_transcript(transcript_text, video_id=None):
    """
    Extract insights from a full transcript.
    
    Args:
        transcript_text (str): The full transcript text
        video_id (str): Optional video ID for context
    
    Returns:
        dict: Extracted insights
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are an expert at extracting insights from transcripts."},
                {"role": "user", "content": INSIGHT_PROMPT + transcript_text}
            ]
        )
        
        insight_json = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if insight_json.startswith("```json"):
            insight_json = insight_json[7:]  # Remove ```json
        if insight_json.startswith("```"):
            insight_json = insight_json[3:]   # Remove ```
        if insight_json.endswith("```"):
            insight_json = insight_json[:-3]  # Remove trailing ```
        
        insight_json = insight_json.strip()
        
        # Try to parse as JSON, fallback to text if needed
        try:
            parsed_json = json.loads(insight_json)
            # Ensure the parsed JSON has the expected structure
            if isinstance(parsed_json, dict):
                return {
                    "summary": parsed_json.get("summary", "No summary provided"),
                    "insights": parsed_json.get("insights", []),
                    "golden_nuggets": parsed_json.get("golden_nuggets", []),
                    "video_id": video_id
                }
            else:
                raise json.JSONDecodeError("Response is not a dictionary", insight_json, 0)
        except json.JSONDecodeError:
            return {
                "summary": "Failed to parse insights as JSON",
                "insights": [],
                "golden_nuggets": [],
                "video_id": video_id,
                "raw_response": insight_json
            }
            
    except Exception as e:
        return {
            "summary": f"Error extracting insights: {str(e)}",
            "insights": [],
            "golden_nuggets": [],
            "video_id": video_id,
            "error": str(e)
        }

def extract_insight_from_transcript(transcript_text):
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": "You are an expert at extracting insights from transcripts."},
            {"role": "user", "content": INSIGHT_PROMPT + transcript_text}
        ]
    )
    return response.choices[0].message.content.strip()

def process_transcripts():
    for video_id in os.listdir(TRANSCRIPTS_DIR):
        video_path = os.path.join(TRANSCRIPTS_DIR, video_id)
        if not os.path.isdir(video_path):
            continue

        insights_output_path = os.path.join(INSIGHTS_DIR, f"{video_id}_insights.json")
        insights_data = []

        for transcript_file in sorted(os.listdir(video_path)):
            if not transcript_file.endswith(".txt"):
                continue

            chunk_path = os.path.join(video_path, transcript_file)
            with open(chunk_path, "r", encoding="utf-8") as f:
                transcript_text = f.read().strip()

            print(f"🧠 Extracting insights from {transcript_file}...")
            try:
                insight_json = extract_insight_from_transcript(transcript_text)
                insights_data.append({
                    "chunk": transcript_file,
                    "insights": json.loads(insight_json) if insight_json.startswith("{") else insight_json
                })
            except Exception as e:
                print(f"❌ Failed on {transcript_file}: {e}")
                insights_data.append({
                    "chunk": transcript_file,
                    "error": str(e)
                })

        # Save all insights for this video
        with open(insights_output_path, "w", encoding="utf-8") as f:
            json.dump(insights_data, f, indent=2)
        print(f"✅ Saved insights for {video_id} to {insights_output_path}")

if __name__ == "__main__":
    process_transcripts()
