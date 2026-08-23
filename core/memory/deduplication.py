"""
Semantic Deduplication Engine for Torchlight.

Provides content-aware deduplication to reduce context tokens by:
- Detecting repeated file contents across turns
- Merging similar tool results (same file reads, similar grep outputs)
- Identifying and referencing previous explanations instead of repeating
- Tracking "concepts explained" to avoid re-explanation
- Semantic similarity detection for assistant responses
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from difflib import SequenceMatcher


@dataclass
class ContentFingerprint:
    """Represents a content fingerprint for deduplication."""
    hash: str
    content_type: str  # "code", "text", "tool_result", "explanation"
    source_index: int
    metadata: dict = field(default_factory=dict)


@dataclass
class DeduplicationStats:
    """Statistics about deduplication effectiveness."""
    total_messages: int = 0
    deduplicated_messages: int = 0
    tokens_saved: int = 0
    file_reads_deduped: int = 0
    grep_results_deduped: int = 0
    search_ast_deduped: int = 0
    explanations_deduped: int = 0


class ContentFingerprinter:
    """Generate semantic hashes for message content."""

    def __init__(self, tokenizer=None):
        self.tokenizer = tokenizer
        self._file_content_cache: dict[str, str] = {}  # path -> content hash
        self._tool_result_cache: dict[str, ContentFingerprint] = {}
        self._concept_fingerprints: dict[str, int] = {}  # concept_hash -> first_index

    def fingerprint(self, content: str, content_type: str = "text", metadata: dict = None) -> ContentFingerprint:
        """Generate a fingerprint for content based on its type."""
        metadata = metadata or {}
        
        if content_type == "tool_result":
            return self._fingerprint_tool_result(content, metadata)
        elif content_type == "code":
            return self._fingerprint_code(content, metadata)
        elif content_type == "explanation":
            return self._fingerprint_explanation(content, metadata)
        else:
            return self._fingerprint_text(content, metadata)

    def _fingerprint_text(self, content: str, metadata: dict) -> ContentFingerprint:
        """Fingerprint general text content using MinHash-style approach."""
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', content.strip())
        # Use first 500 chars + last 500 chars for large content
        if len(normalized) > 1000:
            sample = normalized[:500] + normalized[-500:]
        else:
            sample = normalized
        hash_val = hashlib.sha256(sample.encode()).hexdigest()[:16]
        return ContentFingerprint(
            hash=hash_val,
            content_type="text",
            source_index=metadata.get("index", 0),
            metadata=metadata
        )

    def _fingerprint_code(self, content: str, metadata: dict) -> ContentFingerprint:
        """Fingerprint code content using structural hashing."""
        # Extract function/class signatures for structural fingerprint
        signatures = re.findall(r'^(?:def|class|async def|function|const|let|var)\s+([a-zA-Z_]\w*)', content, re.MULTILINE)
        struct_content = "\n".join(sorted(signatures)) + "\n" + content[:1000]
        hash_val = hashlib.sha256(struct_content.encode()).hexdigest()[:16]
        return ContentFingerprint(
            hash=hash_val,
            content_type="code",
            source_index=metadata.get("index", 0),
            metadata={**metadata, "signatures": signatures}
        )

    def _fingerprint_tool_result(self, content: str, metadata: dict) -> ContentFingerprint:
        """Fingerprint tool results with special handling for file reads, grep, etc."""
        tool_name = metadata.get("tool_name", "")
        
        if tool_name == "READ_FILE":
            path = metadata.get("path", "")
            start_line = metadata.get("start_line", 0)
            end_line = metadata.get("end_line", 0)
            # Hash path + line range + content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            fp_hash = hashlib.sha256(f"{path}:{start_line}:{end_line}:{content_hash}".encode()).hexdigest()[:16]
            cache_key = f"{path}:{start_line}:{end_line}"
            
            # Check cache for repeated reads
            if cache_key in self._file_content_cache:
                cached_hash = self._file_content_cache[cache_key]
                if cached_hash == content_hash:
                    return ContentFingerprint(
                        hash=fp_hash,
                        content_type="tool_result",
                        source_index=metadata.get("index", 0),
                        metadata={**metadata, "deduped": True, "original_hash": cached_hash}
                    )
            
            self._file_content_cache[cache_key] = content_hash
            return ContentFingerprint(
                hash=fp_hash,
                content_type="tool_result",
                source_index=metadata.get("index", 0),
                metadata={**metadata, "file_path": path, "content_hash": content_hash}
            )
            
        elif tool_name in ("GREP", "SEARCH_AST"):
            # Hash pattern + results summary
            pattern = metadata.get("pattern", metadata.get("query", ""))
            # Normalize results for comparison
            lines = content.splitlines()
            result_summary = f"{len(lines)} lines, {len(content)} chars"
            if lines:
                result_summary += f", first: {lines[0][:100]}"
            fp_hash = hashlib.sha256(f"{tool_name}:{pattern}:{result_summary}".encode()).hexdigest()[:16]
            
            return ContentFingerprint(
                hash=fp_hash,
                content_type="tool_result",
                source_index=metadata.get("index", 0),
                metadata={**metadata, "pattern": pattern, "result_summary": result_summary}
            )
            
        else:
            # Generic tool result
            normalized = re.sub(r'\s+', ' ', content.strip())
            hash_val = hashlib.sha256(f"{tool_name}:{normalized[:500]}".encode()).hexdigest()[:16]
            return ContentFingerprint(
                hash=hash_val,
                content_type="tool_result",
                source_index=metadata.get("index", 0),
                metadata={**metadata, "tool_name": tool_name}
            )

    def _fingerprint_explanation(self, content: str, metadata: dict) -> ContentFingerprint:
        """Fingerprint explanatory content to track concepts explained."""
        # Extract key terms/concepts
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        # Filter common words
        stop_words = {'this', 'that', 'with', 'from', 'have', 'will', 'been', 'were', 'they', 'their', 'them', 'would', 'could', 'should', 'about', 'after', 'before', 'between', 'through', 'during', 'under', 'above', 'below', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose', 'each', 'every', 'other', 'another', 'such', 'only', 'own', 'same', 'than', 'too', 'very', 'can', 'just', 'now', 'also', 'may', 'must', 'might', 'need', 'ought', 'shall', 'used', 'using', 'use', 'make', 'made', 'does', 'did', 'doing', 'done'}
        concepts = [w for w in words if w not in stop_words and len(w) > 3]
        concept_set = frozenset(concepts[:50])  # Top 50 concepts
        concept_hash = hashlib.sha256(str(sorted(concept_set)).encode()).hexdigest()[:16]
        
        return ContentFingerprint(
            hash=concept_hash,
            content_type="explanation",
            source_index=metadata.get("index", 0),
            metadata={**metadata, "concepts": list(concept_set)[:20]}
        )


class SimilarityDetector:
    """Identify similar content across turns using various similarity metrics."""

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity ratio between two strings."""
        return SequenceMatcher(None, a, b).ratio()

    def jaccard_similarity(self, set_a: set, set_b: set) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def find_similar(self, fingerprints: list[ContentFingerprint], new_fp: ContentFingerprint) -> Optional[ContentFingerprint]:
        """Find if a new fingerprint is similar to any existing one."""
        for fp in fingerprints:
            if fp.content_type != new_fp.content_type:
                continue
            
            if fp.content_type == "tool_result":
                # For tool results, check specific metadata
                if fp.metadata.get("tool_name") == new_fp.metadata.get("tool_name"):
                    if fp.metadata.get("tool_name") == "READ_FILE":
                        if fp.metadata.get("file_path") == new_fp.metadata.get("file_path"):
                            if fp.metadata.get("content_hash") == new_fp.metadata.get("content_hash"):
                                return fp
                    elif fp.metadata.get("tool_name") in ("GREP", "SEARCH_AST"):
                        if fp.metadata.get("pattern") == new_fp.metadata.get("pattern"):
                            # Check if results are very similar
                            sim = self.similarity(
                                fp.metadata.get("result_summary", ""),
                                new_fp.metadata.get("result_summary", "")
                            )
                            if sim > self.threshold:
                                return fp
            elif fp.content_type == "explanation":
                # Check concept overlap
                concepts_a = set(fp.metadata.get("concepts", []))
                concepts_b = set(new_fp.metadata.get("concepts", []))
                sim = self.jaccard_similarity(concepts_a, concepts_b)
                if sim > self.threshold:
                    return fp
            else:
                # General text similarity
                sim = self.similarity(fp.hash, new_fp.hash)
                if sim > self.threshold:
                    return fp
        return None


class ConceptTracker:
    """Track explained concepts to avoid repetition."""

    def __init__(self):
        self.explained_concepts: dict[str, int] = {}  # concept -> first_explanation_index
        self.concept_contexts: dict[str, str] = {}  # concept -> context summary

    def track_explanation(self, content: str, index: int) -> list[str]:
        """Extract and track concepts from an explanation."""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        stop_words = {'this', 'that', 'with', 'from', 'have', 'will', 'been', 'were', 'they', 'their', 'them', 'would', 'could', 'should', 'about', 'after', 'before', 'between', 'through', 'during', 'under', 'above', 'below', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose', 'each', 'every', 'other', 'another', 'such', 'only', 'own', 'same', 'than', 'too', 'very', 'can', 'just', 'now', 'also', 'may', 'must', 'might', 'need', 'ought', 'shall', 'used', 'using', 'use', 'make', 'made', 'does', 'did', 'doing', 'done'}
        concepts = [w for w in words if w not in stop_words and len(w) > 3]
        
        new_concepts = []
        for concept in concepts[:30]:  # Track top 30
            if concept not in self.explained_concepts:
                self.explained_concepts[concept] = index
                self.concept_contexts[concept] = content[:200]
                new_concepts.append(concept)
        
        return new_concepts

    def is_explained(self, concept: str) -> bool:
        """Check if a concept has been explained before."""
        return concept in self.explained_concepts

    def get_explanation_context(self, concept: str) -> Optional[str]:
        """Get the context where a concept was first explained."""
        return self.concept_contexts.get(concept)

    def get_unexplained_concepts(self, content: str) -> list[str]:
        """Get concepts in content that haven't been explained yet."""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        stop_words = {'this', 'that', 'with', 'from', 'have', 'will', 'been', 'were', 'they', 'their', 'them', 'would', 'could', 'should', 'about', 'after', 'before', 'between', 'through', 'during', 'under', 'above', 'below', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose', 'each', 'every', 'other', 'another', 'such', 'only', 'own', 'same', 'than', 'too', 'very', 'can', 'just', 'now', 'also', 'may', 'must', 'might', 'need', 'ought', 'shall', 'used', 'using', 'use', 'make', 'made', 'does', 'did', 'doing', 'done'}
        concepts = [w for w in words if w not in stop_words and len(w) > 3]
        return [c for c in concepts[:30] if c not in self.explained_concepts]


class DeduplicationEngine:
    """Main deduplication engine integrating all components."""

    def __init__(self, tokenizer=None, similarity_threshold: float = 0.85):
        self.fingerprinter = ContentFingerprinter(tokenizer)
        self.similarity_detector = SimilarityDetector(similarity_threshold)
        self.concept_tracker = ConceptTracker()
        self.stats = DeduplicationStats()
        self._fingerprints: list[ContentFingerprint] = []
        self._deduped_indices: set[int] = set()

    def process_messages(self, messages: list) -> tuple[list, DeduplicationStats]:
        """Process a list of messages for deduplication.
        
        Returns deduplicated messages and stats.
        """
        self.stats = DeduplicationStats()
        self.stats.total_messages = len(messages)
        self._fingerprints = []
        self._deduped_indices = set()
        
        deduplicated = []
        
        for i, msg in enumerate(messages):
            # Determine content type and extract metadata
            content = getattr(msg, 'content', str(msg))
            role = getattr(msg, 'role', 'unknown')
            metadata = getattr(msg, 'metadata', {})
            metadata['index'] = i
            
            # Determine content type
            if role == 'tool_result' or metadata.get('tool_name'):
                content_type = 'tool_result'
                metadata['tool_name'] = metadata.get('tool_name', '')
            elif self._is_code_content(content):
                content_type = 'code'
            elif self._is_explanation(content):
                content_type = 'explanation'
            else:
                content_type = 'text'
            
            # Generate fingerprint
            fp = self.fingerprinter.fingerprint(content, content_type, metadata)

            # Only tool_result content is eligible for reference-replacement deduplication
            if content_type != 'tool_result':
                if content_type == 'explanation':
                    self.concept_tracker.track_explanation(content, i)
                self._fingerprints.append(fp)
                deduplicated.append(msg)
                continue

            # Check for similarity in prior tool results
            similar_fp = self.similarity_detector.find_similar(self._fingerprints, fp)
            
            if similar_fp and not similar_fp.metadata.get('deduped', False):
                # Create reference message instead of full content for duplicate tool results
                ref_msg = self._create_reference_message(
                    msg, similar_fp, fp, content_type
                )
                deduplicated.append(ref_msg)
                self._deduped_indices.add(i)
                self.stats.deduplicated_messages += 1
                
                # Update stats based on tool type
                tool_name = metadata.get('tool_name', '')
                if tool_name == 'READ_FILE':
                    self.stats.file_reads_deduped += 1
                elif tool_name == 'GREP':
                    self.stats.grep_results_deduped += 1
                elif tool_name == 'SEARCH_AST':
                    self.stats.search_ast_deduped += 1
                
                # Estimate tokens saved
                original_tokens = self._estimate_tokens(content)
                ref_tokens = self._estimate_tokens(str(ref_msg))
                self.stats.tokens_saved += max(0, original_tokens - ref_tokens)
            else:
                self._fingerprints.append(fp)
                deduplicated.append(msg)
        
        return deduplicated, self.stats

    def _is_code_content(self, content: str) -> bool:
        """Heuristic to detect code content."""
        code_patterns = [
            r'^\s*(def|class|function|const|let|var)\s+\w+',
            r'^\s*(import|from|export|require)\s+',
            r'^\s*#include\s+',
            r'^\s*public\s+class',
            r'^\s*fn\s+\w+',
            r'^\s*func\s+\w+',
        ]
        for pattern in code_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def _is_explanation(self, content: str) -> bool:
        """Heuristic to detect explanatory content."""
        explanation_indicators = [
            'explain', 'because', 'reason', 'therefore', 'thus',
            'this means', 'in other words', 'to clarify', 'note that',
            'important', 'key concept', 'understand', 'works by',
            'how it works', 'the way', 'mechanism', 'algorithm',
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in explanation_indicators) and len(content) > 100

    def _create_reference_message(self, original_msg, similar_fp: ContentFingerprint, new_fp: ContentFingerprint, content_type: str):
        """Create a reference message pointing to the original content."""
        # This would create a lightweight message referencing the original
        # For now, return a modified version of the original message
        ref_content = f"[Deduplicated: See turn {similar_fp.source_index + 1} for {content_type} content]"
        
        # Create a new message object with reduced content
        if hasattr(original_msg, '__class__'):
            # Try to create same type
            try:
                return original_msg.__class__(
                    role=getattr(original_msg, 'role', 'assistant'),
                    content=ref_content,
                    token_count=len(ref_content) // 3,
                    metadata={**getattr(original_msg, 'metadata', {}), 'deduped': True, 'reference_to': similar_fp.source_index}
                )
            except Exception:
                pass
        
        # Fallback: return dict-like object
        return type('Message', (), {
            'role': getattr(original_msg, 'role', 'assistant'),
            'content': ref_content,
            'token_count': len(ref_content) // 3,
            'metadata': {'deduped': True, 'reference_to': similar_fp.source_index}
        })()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        if self.fingerprinter.tokenizer:
            return self.fingerprinter.tokenizer.count(text)
        return max(1, len(text) // 3)

    def reset(self) -> None:
        """Reset the deduplication engine for a new conversation."""
        self.fingerprinter._file_content_cache.clear()
        self.fingerprinter._tool_result_cache.clear()
        self.fingerprinter._concept_fingerprints.clear()
        self.concept_tracker.explained_concepts.clear()
        self.concept_tracker.concept_contexts.clear()
        self._fingerprints.clear()
        self._deduped_indices.clear()

    def get_cache(self) -> dict:
        """Return serializable cache state for persistence."""
        return {
            "file_content_cache": dict(self.fingerprinter._file_content_cache),
            "concept_fingerprints": dict(self.fingerprinter._concept_fingerprints),
            "explained_concepts": dict(self.concept_tracker.explained_concepts),
            "concept_contexts": dict(self.concept_tracker.concept_contexts),
        }

    def load_cache(self, cache: dict) -> None:
        """Restore serializable cache state from persistence."""
        if not cache:
            return
        self.fingerprinter._file_content_cache.update(cache.get("file_content_cache", {}))
        self.fingerprinter._concept_fingerprints.update(cache.get("concept_fingerprints", {}))
        self.concept_tracker.explained_concepts.update(cache.get("explained_concepts", {}))
        self.concept_tracker.concept_contexts.update(cache.get("concept_contexts", {}))


def deduplicate_context(messages: list, tokenizer=None, similarity_threshold: float = 0.85) -> tuple[list, DeduplicationStats]:
    """Convenience function to deduplicate a message list."""
    engine = DeduplicationEngine(tokenizer, similarity_threshold)
    return engine.process_messages(messages)