"""
Unit tests for Enhanced Long-Term Memory Persistence & Hybrid Vector Retrieval.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from core.memory.models import MemoryObject, MemoryNeedle, SessionState
from core.memory.embeddings import (
    tokenize_text,
    compute_tf_idf_score,
    cosine_similarity,
    HybridMemoryRetriever,
    KeywordEmbedder,
)
from core.memory.persistence import ProjectMemory
from core.memory.manager import TieredMemory, MemoryConfig


def test_tokenize_text_and_tf_idf():
    tokens = tokenize_text("Refactored memory module with BM25 vector retrieval!")
    assert "refactored" in tokens
    assert "memory" in tokens
    assert "bm25" in tokens

    score = compute_tf_idf_score(
        ["memory", "bm25"], ["refactored", "memory", "module", "with", "bm25"]
    )
    assert score > 0.0


def test_cosine_similarity():
    vec1 = [1.0, 0.0, 0.5]
    vec2 = [1.0, 0.0, 0.5]
    assert cosine_similarity(vec1, vec2) == pytest.approx(1.0)

    vec3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(vec1, vec3) == 0.0


def test_hybrid_memory_retriever_channel_filtering():
    retriever = HybridMemoryRetriever()

    mem1 = MemoryObject(
        kind="decision",
        summary="Use Telegram bot gateway with asyncio for multi-channel messaging",
        channel_id="telegram",
        vector_tokens=tokenize_text(
            "Use Telegram bot gateway with asyncio for multi-channel messaging"
        ),
    )
    mem2 = MemoryObject(
        kind="decision",
        summary="Use Slack Bolt SDK for enterprise workspace integration",
        channel_id="slack",
        vector_tokens=tokenize_text(
            "Use Slack Bolt SDK for enterprise workspace integration"
        ),
    )
    mem3 = MemoryObject(
        kind="fact",
        summary="CLI default persistent memory file is .context-memory.json",
        channel_id="default",
        vector_tokens=tokenize_text(
            "CLI default persistent memory file is .context-memory.json"
        ),
    )

    memories = [mem1, mem2, mem3]

    # Query telegram channel
    results_tg = retriever.retrieve(
        "Telegram gateway messaging", memories, channel_id="telegram", top_k=5
    )
    assert len(results_tg) >= 1
    assert any(m[0].channel_id == "telegram" for m in results_tg)
    assert not any(m[0].channel_id == "slack" for m in results_tg)

    # Query slack channel
    results_slack = retriever.retrieve(
        "Slack Bolt workspace", memories, channel_id="slack", top_k=5
    )
    assert len(results_slack) >= 1
    assert any(m[0].channel_id == "slack" for m in results_slack)
    assert not any(m[0].channel_id == "telegram" for m in results_slack)


def test_project_memory_add_and_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectMemory(tmpdir)

        mo1 = MemoryObject(
            kind="arch_decision",
            summary="Decoupled core memory from CLI frontend using hybrid retrieval",
            channel_id="discord",
            vector_tokens=tokenize_text(
                "Decoupled core memory from CLI frontend using hybrid retrieval"
            ),
            ast_symbols=["TieredMemory", "ProjectMemory"],
        )
        pm.add_memory_object(mo1)

        loaded_objs = pm.get_memory_objects(channel_id="discord")
        assert len(loaded_objs) == 1
        assert loaded_objs[0].summary == mo1.summary
        assert loaded_objs[0].channel_id == "discord"
        assert "TieredMemory" in loaded_objs[0].ast_symbols

        # Search memory
        search_res = pm.search_memory(
            "hybrid retrieval core memory", channel_id="discord"
        )
        assert len(search_res) == 1
        assert search_res[0][0].summary == mo1.summary


def test_tiered_memory_l3_scratchpad_surfacing():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectMemory(tmpdir)
        mo = MemoryObject(
            kind="decision",
            summary="Optimized KV cache with 4-bit TurboQuant on 8GB Mac",
            channel_id="default",
            vector_tokens=tokenize_text(
                "Optimized KV cache with 4-bit TurboQuant on 8GB Mac"
            ),
        )
        pm.add_memory_object(mo)

        cfg = MemoryConfig(max_tokens=4000)
        tm = TieredMemory(config=cfg, project_memory=pm)
        tm.state.current_task = "Optimize KV cache for 8GB device"

        scratchpad = tm.format_l0_scratchpad()
        assert "[L0 WORKING MEMORY SCRATCHPAD]" in scratchpad
        assert (
            "Facts & Past Context" in scratchpad or "Relevant L3 Context" in scratchpad
        )
        assert "TurboQuant" in scratchpad


def test_l0_scratchpad_priority_weighted_order():
    cfg = MemoryConfig(max_tokens=12288)
    tm = TieredMemory(config=cfg)

    # Populate 8 priority levels
    tm.state.errors_seen = [
        "Err1",
        "Err2",
        "Err3",
    ]  # all surface on roomy 12k window (cap 8)
    tm.state.failing_tests = ["tests/test_auth.py::test_login_failure"]  # name only
    tm.state.current_task = "Fix authentication bug"
    tm.state.active_file = "src/auth.py"
    tm.state.decisions = [
        "Dec1",
        "Dec2",
        "Dec3",
        "Dec4",
    ]  # all surface on roomy 12k window (cap 8)
    tm.state.files_modified = ["src/a.py", "src/b.py", "src/c.py", "src/d.py"]  # last 3
    tm.state.tech_stack = ["Python 3.9", "FastAPI"]
    tm.state.tried_and_failed = ["Failed auth retry strategy"]

    scratchpad = tm.format_l0_scratchpad()
    lines = scratchpad.split("\n")

    # Verify priority order:
    # 1. Active Errors (Err2, Err3)
    # 2. Failing Tests (test_login_failure)
    # 3. Active Goal / Active File
    # 4. Key Decisions (Dec2, Dec3, Dec4)
    # 5. Modified Files (b.py, c.py, d.py)
    # 6. Tech Stack
    # 7. Tried & Failed
    err_idx = next(i for i, l in enumerate(lines) if "Active Errors" in l)
    test_idx = next(i for i, l in enumerate(lines) if "Failing Tests" in l)
    goal_idx = next(i for i, l in enumerate(lines) if "Active Goal" in l)
    dec_idx = next(i for i, l in enumerate(lines) if "Key Decisions" in l)
    mod_idx = next(i for i, l in enumerate(lines) if "Modified Files" in l)
    tech_idx = next(i for i, l in enumerate(lines) if "Tech Stack" in l)
    tf_idx = next(i for i, l in enumerate(lines) if "Tried & Failed" in l)

    assert err_idx < test_idx < goal_idx < dec_idx < mod_idx < tech_idx < tf_idx
    assert "Err1" in scratchpad  # roomy 12k window: section cap expands to 8
    assert "Dec1" in scratchpad  # roomy 12k window: section cap expands to 8
    assert "src/a.py" not in scratchpad  # capped at last 3 modified files
