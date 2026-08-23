# UI Chat Improvements Plan - Minimal Context & Token Savings

## Goal
Improve the chat UI to feel more like Claude Code while minimizing context usage and saving tokens through semantic deduplication, targeting both 4K and 12K context models.

## Current Architecture Analysis

### Strengths
- Tiered memory system (L0-L3) with progressive compression (FULL→COMPACT→SUMMARY→HINT)
- Dynamic L0 Working Memory Scratchpad with headroom-adaptive budget
- Active file pinning (FIFO, max 4 files)
- Selective compression preserving decisions/errors
- Streaming view with token-by-token updates
- Bounded transcript container (MAX_CHILDREN=35)

### Areas for Improvement

#### 1. Message Rendering & Formatting (Claude Code-like Experience)
- **Current**: Basic Markdown cards with simple headers
- **Target**: Rich message cards with:
  - Syntax-highlighted code blocks with copy buttons
  - Collapsible tool call/result sections
  - Inline token counts per message
  - Visual distinction for tool calls vs conversational text
  - Better markdown rendering (tables, lists, checkboxes)
  - Avatars/role indicators matching Claude Code aesthetic

#### 2. Semantic Deduplication for Token Savings
- **Current**: Progressive compression by message age only
- **Target**: Content-aware deduplication:
  - Detect repeated file contents across turns
  - Merge similar tool results (same file reads, similar grep outputs)
  - Identify and reference previous explanations instead of repeating
  - Track "concepts explained" to avoid re-explanation
  - Semantic similarity detection for assistant responses

#### 3. Context Optimization for 4K/12K Models
- **Current**: Fixed budgets, simple truncation
- **Target**: Adaptive context management:
  - Model-aware budget allocation (4K vs 12K configs)
  - Priority-based retention (errors > decisions > file contents > general chat)
  - Smart L0 scratchpad sizing based on available headroom
  - Dynamic pinned file budget based on context pressure

## Implementation Plan

### Phase 1: Enhanced Message Rendering (Claude Code UX)

#### 1.1 Rich Message Card Component
- **File**: `rlm_optimized/tui_widgets/transcript.py`
- **Changes**:
  - Replace basic `Markdown` widget with custom `RichMessageCard`
  - Add syntax highlighting for code blocks using `rich.syntax.Syntax`
  - Add copy-to-clipboard buttons for code blocks
  - Implement collapsible sections for tool calls/results
  - Add per-message token count display
  - Improve visual hierarchy with better spacing/typography

#### 1.2 Streaming Experience Improvements
- **File**: `rlm_optimized/tui_widgets/transcript.py`
- **Changes**:
  - Enhanced `StreamingView` with live token count
  - Smooth scrolling during streaming
  - Better visual feedback for tool call streaming
  - Phase-aware streaming indicators

#### 1.3 Transcript Container Enhancements
- **File**: `rlm_optimized/tui_widgets/transcript.py`
- **Changes**:
  - Virtual scrolling for large transcripts
  - Message grouping by conversation turns
  - Keyboard navigation (j/k, g/G, search)
  - Context menu for copy/export actions

### Phase 2: Semantic Deduplication Engine

#### 2.1 Content Fingerprinting System
- **New File**: `core/memory/deduplication.py`
- **Components**:
  - `ContentFingerprinter`: Generate semantic hashes for message content
  - `SimilarityDetector`: Identify similar content across turns (Jaccard/MinHash)
  - `ConceptTracker`: Track explained concepts to avoid repetition

#### 2.2 Deduplication-Aware Compression
- **File**: `core/memory/manager.py` (extend `TieredMemory`)
- **Changes**:
  - Add `deduplicate_context()` method
  - Integrate with `compress_recent()` pipeline
  - Preserve first occurrence, reference subsequent ones
  - Maintain semantic equivalence while reducing tokens

#### 2.3 Tool Result Deduplication
- **File**: `core/memory/manager.py`
- **Changes**:
  - Detect repeated `READ_FILE` of same file/range
  - Merge similar `GREP`/`SEARCH_AST` results
  - Cache file contents with version tracking

### Phase 3: Adaptive Context Management

#### 3.1 Model-Aware Configuration
- **File**: `rlm_optimized/config.py` (extend)
- **Changes**:
  - Add `ContextProfile` enum (SMALL_4K, MEDIUM_8K, LARGE_12K, XLARGE_32K)
  - Auto-detect model context window
  - Profile-specific budget allocations

#### 3.2 Dynamic Budget Allocation
- **File**: `core/memory/budget.py` (extend `ContextBudget`)
- **Changes**:
  - Priority-based token allocation:
    1. System prompt + tool schemas (fixed)
    2. L0 Scratchpad (adaptive, 5-15%)
    3. Recent messages (priority: errors > decisions > file ops > chat)
    4. Pinned files (adaptive, 3-10%)
    5. Compressed history (remaining)
  - Real-time adjustment based on context pressure

#### 3.3 Smart L0 Scratchpad
- **File**: `core/memory/manager.py` (extend `format_l0_scratchpad`)
- **Changes**:
  - Content-aware entry selection (not just priority-ordered)
  - Deduplication within scratchpad
  - Dynamic sizing based on model profile

### Phase 4: Integration & Polish

#### 4.1 Engine Integration
- **File**: `rlm_optimized/rlm_engine_optimized.py`
- **Changes**:
  - Call deduplication before context building
  - Pass model profile to memory system
  - Add metrics for deduplication effectiveness

#### 4.2 TUI Integration
- **File**: `rlm_optimized/tui_app.py`
- **Changes**:
  - Display deduplication stats in status bar
  - Show context profile indicator
  - Add manual deduplication trigger (Ctrl+D)

#### 4.3 Configuration & Persistence
- **Files**: `rlm_optimized/config.py`, `core/memory/persistence.py`
- **Changes**:
  - Persist deduplication cache across sessions
  - User preferences for compression aggressiveness
  - Export/import context profiles

## Technical Details

### Semantic Deduplication Algorithm

```python
# Pseudocode for deduplication pipeline
def deduplicate_context(messages: list[Message]) -> list[Message]:
    fingerprints = {}
    deduplicated = []
    
    for msg in messages:
        fp = content_fingerprinter.fingerprint(msg.content)
        
        if fp in fingerprints:
            # Reference previous occurrence
            ref_msg = create_reference_message(
                original_index=fingerprints[fp],
                current_index=len(deduplicated)
            )
            deduplicated.append(ref_msg)
        else:
            fingerprints[fp] = len(deduplicated)
            deduplicated.append(msg)
    
    return deduplicated
```

### Content Fingerprinting Strategy

1. **Structural Fingerprinting**: Hash normalized AST structure for code
2. **Semantic Fingerprinting**: MinHash for natural language content
3. **Tool Result Fingerprinting**: Hash file path + line range + content hash
4. **Concept Fingerprinting**: Extract key terms/entities, hash concept set

### Priority-Based Retention

```python
MESSAGE_PRIORITY = {
    "tool_error": 1.0,      # Always keep
    "architecture_decision": 0.9,
    "file_modification": 0.8,
    "file_read": 0.7,
    "tool_success": 0.6,
    "user_question": 0.5,
    "assistant_explanation": 0.4,
    "general_chat": 0.3,
}
```

## Validation Plan

### Metrics to Track
1. **Token Reduction**: % tokens saved vs baseline
2. **Semantic Preservation**: Human evaluation of context quality
3. **Response Quality**: Model performance on coding tasks
4. **Latency**: Compression/deduplication overhead
5. **UX Metrics**: User satisfaction with message rendering

### Test Scenarios
1. **Long Conversation**: 50+ turns with repeated file reads
2. **Code Review Session**: Multiple similar GREP/SEARCH_AST results
3. **Debugging Session**: Repeated error contexts
4. **Multi-file Refactoring**: Cross-file references
5. **Small Context (4K)**: Stress test with aggressive compression

### A/B Testing
- Compare baseline vs deduplication on same conversation
- Measure token usage, model accuracy, user preference

## Rollout Strategy

1. **Phase 1** (Week 1): Enhanced message rendering (UI only, no behavior change)
2. **Phase 2** (Week 2): Semantic deduplication engine (off by default, feature flag)
3. **Phase 3** (Week 3): Adaptive context management with model profiles
4. **Phase 4** (Week 4): Integration, testing, polish, documentation

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Over-aggressive deduplication loses context | High | Conservative thresholds, human review, rollback |
| Fingerprinting false positives | Medium | Multiple fingerprint strategies, similarity thresholds |
| Performance overhead | Low | Async deduplication, caching, incremental updates |
| UX regression | Medium | Feature flags, gradual rollout, user feedback |

## Success Criteria

1. **Token Savings**: ≥30% reduction in context tokens for typical sessions
2. **Claude Code Parity**: Message rendering matches or exceeds Claude Code UX
3. **Model Performance**: No degradation in coding task success rate
4. **Latency**: <50ms additional overhead per turn
5. **User Satisfaction**: Positive feedback on context awareness and UI polish