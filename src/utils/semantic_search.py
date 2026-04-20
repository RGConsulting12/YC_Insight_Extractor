"""
Semantic search module for transcript-based RAG search
Uses OpenAI embeddings to enable semantic search across video transcripts
"""
import os
import json
import numpy as np
import sys
import traceback
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# #region agent log
def _debug_log(hypothesis_id: str, location: str, message: str, data: dict):
    """Helper to write debug logs with memory info - FLUSH IMMEDIATELY for crash debugging"""
    try:
        import time as time_module
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        data['memory_rss_mb'] = round(mem_info.rss / 1024 / 1024, 2)
        data['memory_vms_mb'] = round(mem_info.vms / 1024 / 1024, 2)
    except ImportError:
        data['memory_rss_mb'] = 'psutil not installed'
    except Exception as e:
        data['memory_rss_mb'] = f'error: {e}'
    
    try:
        import time as time_module
        log_path = '/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log'
        with open(log_path, 'a') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "embedding-test-v2",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time_module.time() * 1000)
            }) + '\n')
            f.flush()  # Force flush to Python buffer
            os.fsync(f.fileno())  # Force OS to write to disk
    except Exception as e:
        print(f"Debug log error: {e}")
# #endregion

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Embedding model
EMBEDDING_MODEL = "text-embedding-3-small"  # Cost-effective, good quality
EMBEDDING_DIM = 1536  # Dimension for text-embedding-3-small

# Chunk size for transcript splitting (for better search granularity)
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks


class SemanticSearch:
    """Semantic search using OpenAI embeddings"""
    
    def __init__(self, project_root: Path, embeddings_file: Optional[Path] = None, transcripts_dir: Optional[Path] = None):
        self.project_root = project_root
        # Use provided transcripts_dir or default to standard location
        if transcripts_dir:
            self.transcripts_dir = Path(transcripts_dir)
        else:
            self.transcripts_dir = project_root / "src" / "transcript" / "data" / "raw_transcripts"
        
        # Ensure transcripts_dir is an absolute path
        if not self.transcripts_dir.is_absolute():
            self.transcripts_dir = self.transcripts_dir.resolve()
        self.embeddings_file = embeddings_file or (project_root / "data" / "embeddings.json")
        self.embeddings_file.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings_cache: Dict[str, List[Dict]] = {}
        
        # #region agent log
        dir_contents = []
        if self.transcripts_dir.exists():
            try:
                dir_contents = os.listdir(str(self.transcripts_dir))[:10]  # First 10 files
            except Exception as e:
                dir_contents = [f"Error listing: {e}"]
        _debug_log("H1", "semantic_search.py:__init__", "SemanticSearch initialized", {
            "project_root": str(project_root),
            "transcripts_dir": str(self.transcripts_dir),
            "transcripts_dir_exists": self.transcripts_dir.exists(),
            "transcripts_dir_contents": dir_contents,
            "embeddings_file": str(self.embeddings_file),
            "embeddings_file_exists": self.embeddings_file.exists()
        })
        # #endregion
        
        self._load_embeddings()
    
    def _load_embeddings(self):
        """Load embeddings from cache file"""
        if self.embeddings_file.exists():
            try:
                with open(self.embeddings_file, 'r', encoding='utf-8') as f:
                    self.embeddings_cache = json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading embeddings cache: {e}")
                self.embeddings_cache = {}
    
    def _save_embeddings(self):
        """Save embeddings to cache file"""
        try:
            # #region agent log
            # Calculate total cache size
            total_embeddings = sum(len(v) for v in self.embeddings_cache.values())
            _debug_log("H4", "semantic_search.py:_save_embeddings", "Starting save", {
                "embeddings_file": str(self.embeddings_file),
                "cache_video_count": len(self.embeddings_cache),
                "total_embeddings": total_embeddings
            })
            # #endregion
            
            # First serialize to string to check size before writing
            json_str = json.dumps(self.embeddings_cache, indent=2, ensure_ascii=False)
            json_size_mb = len(json_str) / (1024 * 1024)
            
            # #region agent log
            _debug_log("H4", "semantic_search.py:_save_embeddings", "JSON serialized", {
                "json_size_mb": json_size_mb,
                "json_length_chars": len(json_str)
            })
            # #endregion
            
            with open(self.embeddings_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            # #region agent log
            file_size = self.embeddings_file.stat().st_size if self.embeddings_file.exists() else 0
            _debug_log("H4", "semantic_search.py:_save_embeddings", "Save completed", {
                "embeddings_file": str(self.embeddings_file),
                "file_size_bytes": file_size,
                "file_size_mb": file_size / (1024 * 1024)
            })
            # #endregion
        except Exception as e:
            print(f"⚠️  Error saving embeddings cache: {e}")
            # #region agent log
            _debug_log("H4", "semantic_search.py:_save_embeddings", "Save FAILED", {
                "embeddings_file": str(self.embeddings_file),
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            # #endregion
    
    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Tuple[str, int, int]]:
        """
        Split text into overlapping chunks
        Returns: List of (chunk_text, start_pos, end_pos) tuples
        """
        # #region agent log
        _debug_log("H7", "semantic_search.py:_chunk_text", "Chunking START", {
            "text_length": len(text),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "expected_chunks": len(text) // (chunk_size - overlap) + 1
        })
        # #endregion
        
        chunks = []
        start = 0
        text_length = len(text)
        iteration = 0
        max_iterations = 1000  # Safety limit
        
        while start < text_length:
            iteration += 1
            
            # Safety check for infinite loop
            if iteration > max_iterations:
                # #region agent log
                _debug_log("H7", "semantic_search.py:_chunk_text", "INFINITE LOOP DETECTED", {
                    "iteration": iteration,
                    "start": start,
                    "text_length": text_length
                })
                # #endregion
                print(f"⚠️  Chunking safety limit reached at iteration {iteration}")
                break
            
            # Log every 10th iteration
            if iteration % 10 == 1:
                # #region agent log
                _debug_log("H7", "semantic_search.py:_chunk_text", f"Chunking iteration {iteration}", {
                    "iteration": iteration,
                    "start": start,
                    "text_length": text_length,
                    "chunks_so_far": len(chunks)
                })
                # #endregion
            
            end = min(start + chunk_size, text_length)
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence endings
                for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                    last_punct = chunk.rfind(punct)
                    if last_punct > chunk_size * 0.5:  # Only break if we're past halfway
                        chunk = chunk[:last_punct + 1]
                        end = start + len(chunk)
                        break
            
            chunks.append((chunk, start, end))
            
            # Calculate next start position with overlap
            new_start = end - overlap
            
            # CRITICAL FIX: Ensure we always make forward progress
            # If new_start <= start, we're stuck in an infinite loop
            # This happens when remaining text is smaller than overlap
            if new_start <= start:
                # Force forward progress - move to end (no overlap for final chunk)
                start = end
            else:
                start = new_start
        
        # #region agent log
        _debug_log("H7", "semantic_search.py:_chunk_text", "Chunking COMPLETE", {
            "total_iterations": iteration,
            "chunks_created": len(chunks),
            "text_length": text_length
        })
        # #endregion
        
        return chunks
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text using OpenAI API"""
        # #region agent log
        text_len = len(text) if text else 0
        _debug_log("H3", "semantic_search.py:_get_embedding", "API call starting", {
            "text_length": text_len,
            "text_preview": text[:100] if text else None
        })
        # #endregion
        
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            embedding = response.data[0].embedding
            
            # #region agent log
            _debug_log("H3", "semantic_search.py:_get_embedding", "API call success", {
                "embedding_length": len(embedding) if embedding else 0,
                "embedding_size_bytes": sys.getsizeof(embedding) if embedding else 0
            })
            # #endregion
            
            return embedding
        except Exception as e:
            # #region agent log
            _debug_log("H3", "semantic_search.py:_get_embedding", "API call FAILED", {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
            # #endregion
            print(f"⚠️  Error getting embedding: {e}")
            return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def generate_embeddings_for_video(self, video_id: str, force_regenerate: bool = False) -> bool:
        """
        Generate embeddings for a video's transcript
        Returns: True if successful, False otherwise
        """
        transcript_path = self.transcripts_dir / f"{video_id}.txt"
        
        # #region agent log
        _debug_log("H1", "semantic_search.py:generate_embeddings_for_video", "Function called", {
            "video_id": video_id,
            "transcript_path": str(transcript_path),
            "transcripts_dir": str(self.transcripts_dir),
            "transcript_exists": transcript_path.exists(),
            "force_regenerate": force_regenerate,
            "cache_size": len(self.embeddings_cache)
        })
        # #endregion
        
        if not transcript_path.exists():
            print(f"⚠️  Transcript not found: {transcript_path}")
            # #region agent log
            dir_listing = []
            if self.transcripts_dir.exists():
                try:
                    dir_listing = os.listdir(str(self.transcripts_dir))[:20]
                except Exception as e:
                    dir_listing = [f"Error: {e}"]
            _debug_log("H1", "semantic_search.py:generate_embeddings_for_video", "Transcript NOT FOUND", {
                "video_id": video_id,
                "transcript_path": str(transcript_path),
                "transcripts_dir_exists": self.transcripts_dir.exists(),
                "transcripts_dir_listing": dir_listing
            })
            # #endregion
            return False
        
        # Check if embeddings already exist
        if not force_regenerate and video_id in self.embeddings_cache:
            print(f"✓ Embeddings already exist for {video_id}")
            return True
        
        print(f"📝 Generating embeddings for {video_id}...")
        
        # Read transcript
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript = f.read()
            
            # #region agent log
            _debug_log("H2", "semantic_search.py:generate_embeddings_for_video", "Transcript loaded", {
                "video_id": video_id,
                "transcript_length_chars": len(transcript),
                "transcript_length_kb": len(transcript) / 1024
            })
            # #endregion
        except Exception as e:
            # #region agent log
            _debug_log("H1", "semantic_search.py:generate_embeddings_for_video", "Error reading transcript", {
                "video_id": video_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            # #endregion
            print(f"⚠️  Error reading transcript: {e}")
            return False
        
        # #region agent log
        _debug_log("H6", "semantic_search.py:generate_embeddings_for_video", "About to check empty", {
            "video_id": video_id,
            "transcript_length": len(transcript)
        })
        # #endregion
        
        if not transcript.strip():
            print(f"⚠️  Empty transcript for {video_id}")
            return False
        
        # #region agent log
        _debug_log("H6", "semantic_search.py:generate_embeddings_for_video", "About to chunk transcript", {
            "video_id": video_id,
            "transcript_length": len(transcript),
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP
        })
        # #endregion
        
        # Chunk the transcript
        try:
            chunks = self._chunk_text(transcript)
        except Exception as e:
            # #region agent log
            _debug_log("H6", "semantic_search.py:generate_embeddings_for_video", "Chunking FAILED", {
                "video_id": video_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            # #endregion
            print(f"⚠️  Error chunking transcript: {e}")
            return False
        
        print(f"  Split into {len(chunks)} chunks")
        
        # #region agent log
        _debug_log("H2", "semantic_search.py:generate_embeddings_for_video", "Transcript chunked", {
            "video_id": video_id,
            "transcript_length": len(transcript),
            "chunks_count": len(chunks),
            "avg_chunk_size": len(transcript) / len(chunks) if chunks else 0
        })
        # #endregion
        
        # Generate embeddings for each chunk
        video_embeddings = []
        for i, (chunk_text, start_pos, end_pos) in enumerate(chunks):
            print(f"  Embedding chunk {i+1}/{len(chunks)}...", end='\r')
            
            # #region agent log
            if i % 5 == 0:  # Log every 5th chunk to avoid excessive logging
                _debug_log("H2", "semantic_search.py:generate_embeddings_for_video", f"Processing chunk {i}", {
                    "video_id": video_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "embeddings_so_far": len(video_embeddings),
                    "chunk_text_len": len(chunk_text)
                })
            # #endregion
            
            embedding = self._get_embedding(chunk_text)
            
            if embedding:
                video_embeddings.append({
                    'chunk_index': i,
                    'text': chunk_text,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'embedding': embedding
                })
            else:
                # #region agent log
                _debug_log("H3", "semantic_search.py:generate_embeddings_for_video", "Embedding FAILED for chunk", {
                    "video_id": video_id,
                    "chunk_index": i,
                    "chunk_text_len": len(chunk_text)
                })
                # #endregion
        
        print(f"  ✓ Generated {len(video_embeddings)} embeddings")
        
        # #region agent log
        # Estimate memory usage
        total_embedding_floats = sum(len(e.get('embedding', [])) for e in video_embeddings)
        estimated_embedding_mb = (total_embedding_floats * 8) / (1024 * 1024)  # 8 bytes per float
        _debug_log("H2", "semantic_search.py:generate_embeddings_for_video", "All embeddings generated", {
            "video_id": video_id,
            "embeddings_count": len(video_embeddings),
            "total_embedding_floats": total_embedding_floats,
            "estimated_embedding_mb": estimated_embedding_mb
        })
        # #endregion
        
        # Store in cache
        self.embeddings_cache[video_id] = video_embeddings
        
        # #region agent log
        _debug_log("H4", "semantic_search.py:generate_embeddings_for_video", "About to save embeddings to file", {
            "video_id": video_id,
            "embeddings_file": str(self.embeddings_file),
            "total_videos_in_cache": len(self.embeddings_cache)
        })
        # #endregion
        
        self._save_embeddings()
        
        # #region agent log
        file_size = 0
        if self.embeddings_file.exists():
            file_size = self.embeddings_file.stat().st_size / (1024 * 1024)
        _debug_log("H4", "semantic_search.py:generate_embeddings_for_video", "Embeddings saved", {
            "video_id": video_id,
            "embeddings_file_exists": self.embeddings_file.exists(),
            "embeddings_file_size_mb": file_size
        })
        # #endregion
        
        return True
    
    def generate_embeddings_for_all(self, force_regenerate: bool = False) -> Dict[str, bool]:
        """Generate embeddings for all transcripts"""
        results = {}
        
        if not self.transcripts_dir.exists():
            print(f"⚠️  Transcripts directory not found: {self.transcripts_dir}")
            return results
        
        transcript_files = list(self.transcripts_dir.glob("*.txt"))
        print(f"📚 Found {len(transcript_files)} transcripts")
        
        for transcript_file in transcript_files:
            video_id = transcript_file.stem
            results[video_id] = self.generate_embeddings_for_video(video_id, force_regenerate)
        
        return results
    
    def search(self, query: str, top_k: int = 5, video_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Perform semantic search across transcripts
        Returns: List of results with video_id, chunk_text, similarity_score, and context
        """
        if not query.strip():
            return []
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        # Search across all videos or specified videos
        videos_to_search = video_ids if video_ids else list(self.embeddings_cache.keys())
        
        results = []
        for video_id in videos_to_search:
            if video_id not in self.embeddings_cache:
                continue
            
            # Calculate similarity for each chunk
            for chunk_data in self.embeddings_cache[video_id]:
                similarity = self._cosine_similarity(
                    query_embedding,
                    chunk_data['embedding']
                )
                
                results.append({
                    'video_id': video_id,
                    'chunk_index': chunk_data['chunk_index'],
                    'text': chunk_data['text'],
                    'similarity': similarity,
                    'start_pos': chunk_data['start_pos'],
                    'end_pos': chunk_data['end_pos']
                })
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def search_with_context(self, query: str, top_k: int = 5, video_ids: Optional[List[str]] = None) -> Dict:
        """
        Perform semantic search using RAG (Retrieval-Augmented Generation)
        Uses top-k retrieval with embeddings, then generates natural language answer using LLM
        
        Returns: Dict with 'answer' (LLM-generated answer) and 'sources' (retrieved chunks)
        """
        # #region agent log
        try:
            import json as json_module
            import time as time_module
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"RAG1","location":"semantic_search.py:332","message":"search_with_context() called","data":{"query":query,"top_k":top_k,"video_ids":video_ids,"embeddings_cache_size":len(self.embeddings_cache)},"timestamp":int(time_module.time()*1000)}) + '\n')
        except:
            pass
        # #endregion
        
        # Step 1: Retrieve top-k chunks using embeddings
        search_results = self.search(query, top_k=top_k * 3, video_ids=video_ids)  # Get more for deduplication
        
        # #region agent log
        try:
            import json as json_module
            import time as time_module
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"RAG2","location":"semantic_search.py:345","message":"Top-k retrieval completed","data":{"query":query,"results_count":len(search_results),"top_k":top_k},"timestamp":int(time_module.time()*1000)}) + '\n')
        except:
            pass
        # #endregion
        
        if not search_results:
            return {
                'answer': 'No relevant information found in the transcripts.',
                'sources': []
            }
        
        # Group by video_id and get best match per video
        video_results = {}
        for result in search_results:
            video_id = result['video_id']
            if video_id not in video_results or result['similarity'] > video_results[video_id]['similarity']:
                video_results[video_id] = result
        
        # Sort by similarity and take top_k
        final_results = sorted(video_results.values(), key=lambda x: x['similarity'], reverse=True)[:top_k]
        
        # Step 2: Generate natural language answer using LLM
        # Prepare context from retrieved chunks
        context_chunks = []
        for result in final_results:
            context_chunks.append({
                'video_id': result['video_id'],
                'text': result['text'],
                'similarity': result['similarity']
            })
        
        # Build prompt for LLM
        context_text = "\n\n---\n\n".join([
            f"[Video: {chunk['video_id']}]\n{chunk['text']}"
            for chunk in context_chunks
        ])
        
        rag_prompt = f"""Based on the following transcript excerpts from video interviews, answer the user's question.

User Question: {query}

Relevant Transcript Excerpts:
{context_text}

Instructions:
- Provide a clear, concise answer based on the transcript excerpts above
- If the excerpts don't contain enough information to answer the question, say so
- Cite which video(s) the information comes from when relevant
- Be specific and accurate based on what was actually said in the transcripts

Answer:"""
        
        # #region agent log
        try:
            import json as json_module
            import time as time_module
            with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"RAG3","location":"semantic_search.py:385","message":"About to call LLM for answer generation","data":{"query":query,"context_chunks_count":len(context_chunks),"prompt_length":len(rag_prompt)},"timestamp":int(time_module.time()*1000)}) + '\n')
        except:
            pass
        # #endregion
        
        # Use OpenAI by default, but support Anthropic if configured
        use_anthropic = os.getenv("USE_ANTHROPIC", "false").lower() == "true"
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        try:
            if use_anthropic and anthropic_api_key:
                # Use Anthropic Claude
                try:
                    from anthropic import Anthropic
                    anthropic_client = Anthropic(api_key=anthropic_api_key)
                    response = anthropic_client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1024,
                        temperature=0.3,
                        system="You are a helpful assistant that answers questions based on video transcript excerpts. Provide accurate, concise answers based only on the provided context.",
                        messages=[
                            {"role": "user", "content": rag_prompt}
                        ]
                    )
                    answer = response.content[0].text.strip()
                except ImportError:
                    print("⚠️  Anthropic SDK not installed. Install with: pip install anthropic")
                    use_anthropic = False
                except Exception as e:
                    print(f"⚠️  Anthropic API error: {e}, falling back to OpenAI")
                    use_anthropic = False
            
            if not use_anthropic:
                # Use OpenAI GPT-4o
                response = client.chat.completions.create(
                    model="gpt-4o",
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on video transcript excerpts. Provide accurate, concise answers based only on the provided context."},
                        {"role": "user", "content": rag_prompt}
                    ]
                )
                answer = response.choices[0].message.content.strip()
            
            # #region agent log
            try:
                import json as json_module
                import time as time_module
                with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                    f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"RAG4","location":"semantic_search.py:402","message":"LLM answer generated","data":{"query":query,"answer_length":len(answer),"sources_count":len(final_results)},"timestamp":int(time_module.time()*1000)}) + '\n')
            except:
                pass
            # #endregion
            
            return {
                'answer': answer,
                'sources': final_results
            }
        except Exception as e:
            # #region agent log
            try:
                import json as json_module
                import time as time_module
                with open('/Users/garcia/Documents/Coding/code4AI-governance/Projects/yc-insight-extractor/.cursor/debug.log', 'a') as f:
                    f.write(json_module.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"RAG5","location":"semantic_search.py:415","message":"LLM call failed","data":{"query":query,"error":str(e)},"timestamp":int(time_module.time()*1000)}) + '\n')
            except:
                pass
            # #endregion
            # Fallback: return raw results if LLM call fails
            return {
                'answer': f'Found {len(final_results)} relevant transcript excerpts, but failed to generate answer: {str(e)}',
                'sources': final_results
            }
