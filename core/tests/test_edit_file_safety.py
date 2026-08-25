"""
Safety regression tests for EDIT_FILE.

Each test here corresponds to a verified defect where EDIT_FILE either
destroyed content it was not asked to touch, half-applied an atomic batch,
or accepted malformed line bounds. The common thread is that every one of
these failures was silent: the tool reported success.
"""

import os
import tempfile
import time

from core.tools.implementations import _parse_diff_block, tool_edit_file_impl


def _write(root: str, name: str, text: str) -> str:
    p = os.path.join(root, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


# ── 1. Diff parsing must never fabricate an edit ──────────────────────────


def test_parse_diff_block_never_fabricates_from_unstructured_text():
    """Text with no conflict markers must parse to (None, None), not a guess.

    The old midpoint/blank-line fallbacks split arbitrary prose in half and
    returned it as (old_text, new_text), inventing an edit nobody requested.
    """
    # 6 lines, no markers — previously split at the midpoint.
    text = "alpha = 1\nbeta = 2\ngamma = 3\ndelta = 4\nepsilon = 5\nzeta = 6"
    assert _parse_diff_block(text) == (None, None)

    # Triple blank line — previously split into two halves.
    text2 = "first block of code here\n\n\nsecond block of code here"
    assert _parse_diff_block(text2) == (None, None)


def test_edit_file_word_search_in_old_text_is_not_a_diff_block():
    """A file containing the bare word SEARCH must not route into diff parsing.

    Regression: old_text mentioning SEARCH set diff_attempted, ran the diff
    parser, hit the midpoint fallback, and silently deleted the first half of
    the requested old_text while duplicating the second half.
    """
    with tempfile.TemporaryDirectory() as root:
        original = (
            'SEARCH_PATTERN = "abc"\n'
            "other = 1\n"
            "third = 2\n"
            "fourth = 3\n"
            "fifth = 4\n"
            "sixth = 5\n"
            'KEEP_ME = "critical config"\n'
        )
        p = _write(root, "conf.py", original)

        old = (
            'SEARCH_PATTERN = "abc"\nother = 1\nthird = 2\n'
            "fourth = 3\nfifth = 4\nsixth = 5"
        )
        new = (
            'SEARCH_PATTERN = "xyz"\nother = 1\nthird = 2\n'
            "fourth = 3\nfifth = 4\nsixth = 5"
        )
        tool_edit_file_impl({"path": "conf.py", "old_text": old, "new_text": new}, root)

        result = open(p, encoding="utf-8").read()
        # The actual requested change must have happened...
        assert 'SEARCH_PATTERN = "xyz"' in result
        # ...and nothing else may have been dropped or duplicated.
        assert 'KEEP_ME = "critical config"' in result
        assert result.count("other = 1") == 1
        assert result.count("sixth = 5") == 1


def test_edit_file_equals_divider_alone_is_not_a_diff_block():
    """A `=======` separator comment in real source is not a conflict marker."""
    with tempfile.TemporaryDirectory() as root:
        original = "# =======\nvalue = 1\n# =======\nkeep = 2\n"
        p = _write(root, "d.py", original)
        tool_edit_file_impl(
            {"path": "d.py", "old_text": "value = 1", "new_text": "value = 99"}, root
        )
        result = open(p, encoding="utf-8").read()
        assert "value = 99" in result
        assert "keep = 2" in result


def test_parse_diff_block_still_handles_real_blocks():
    """The structured formats the tool legitimately supports must keep working."""
    canonical = (
        "<<<<<<< SEARCH\ndef foo():\n    return 1\n"
        "=======\ndef foo():\n    return 2\n>>>>>>> REPLACE"
    )
    assert _parse_diff_block(canonical) == (
        "def foo():\n    return 1",
        "def foo():\n    return 2",
    )


# ── 2. Multi-chunk batches must be atomic ─────────────────────────────────


def test_multi_chunk_rolls_back_on_rejected_chunk():
    """Any failing chunk must roll the whole batch back.

    Regression: rollback keyed on the substrings "Error"/"Edit failed", so a
    chunk rejected with "Edit rejected" left earlier chunks committed and let
    later chunks proceed — a half-applied transaction reported as success.
    """
    with tempfile.TemporaryDirectory() as root:
        original = "x = 1\ny = 2\nz = 3\nkeep = 4\n"
        p = _write(root, "a.py", original)

        res = tool_edit_file_impl(
            {
                "path": "a.py",
                "chunks": [
                    {"old_text": "x = 1", "new_text": "x = 100"},
                    {"content": "tiny"},  # rejected: partial content, no anchor
                    {"old_text": "z = 3", "new_text": "z = 300"},
                ],
            },
            root,
        )

        assert open(p, encoding="utf-8").read() == original, "batch was not atomic"
        assert "aborted" in res.lower() or "rolled back" in res.lower()


def test_multi_chunk_does_not_inherit_top_level_anchors():
    """Chunks must not silently inherit top-level old_text/new_text.

    Regression: chunk_args = dict(args) leaked the parent old_text into every
    chunk, so a chunk supplying only new_text edited a location it never named.
    """
    with tempfile.TemporaryDirectory() as root:
        original = "aaa\nbbb\n"
        p = _write(root, "b.py", original)
        tool_edit_file_impl(
            {"path": "b.py", "old_text": "aaa", "chunks": [{"new_text": "ZZZ"}]}, root
        )
        # "aaa" was never named by the chunk, so it must survive.
        assert "aaa" in open(p, encoding="utf-8").read()


def test_multi_chunk_applies_all_valid_chunks():
    """The happy path must still apply every chunk."""
    with tempfile.TemporaryDirectory() as root:
        p = _write(root, "c.py", "x = 1\ny = 2\nz = 3\n")
        tool_edit_file_impl(
            {
                "path": "c.py",
                "chunks": [
                    {"old_text": "x = 1", "new_text": "x = 100"},
                    {"old_text": "z = 3", "new_text": "z = 300"},
                ],
            },
            root,
        )
        result = open(p, encoding="utf-8").read()
        assert "x = 100" in result and "z = 300" in result and "y = 2" in result


# ── 3. Malformed line bounds must be rejected, not scrubbed ───────────────


def test_malformed_line_numbers_are_rejected():
    """Non-numeric line bounds must fail loudly rather than be digit-scraped.

    Regression: end_line="10-20" became 1020 and truncated the file;
    start_line="-2" became 2; start_line="1e5" became 15.
    """
    for start, end in [("-2", "3"), ("2", "10-20"), ("1e5", "2"), ("abc", "4")]:
        with tempfile.TemporaryDirectory() as root:
            original = "l1\nl2\nl3\nl4\nl5\n"
            p = _write(root, "c.py", original)
            res = tool_edit_file_impl(
                {
                    "path": "c.py",
                    "start_line": start,
                    "end_line": end,
                    "new_text": "NEW",
                },
                root,
            )
            assert open(p, encoding="utf-8").read() == original, (
                f"start_line={start!r} end_line={end!r} modified the file"
            )
            assert "failed" in res.lower() or "requires" in res.lower()


def test_valid_string_line_numbers_still_accepted():
    """Plain numeric strings remain valid — models often quote their integers."""
    with tempfile.TemporaryDirectory() as root:
        p = _write(root, "c.py", "l1\nl2\nl3\nl4\nl5\n")
        tool_edit_file_impl(
            {"path": "c.py", "start_line": "2", "end_line": "3", "new_text": "NEW"},
            root,
        )
        result = open(p, encoding="utf-8").read()
        assert "NEW" in result and "l1" in result and "l4" in result


def test_line_reference_prefix_forms_are_accepted():
    """"L4"/"line 4" are formats models really emit and must keep working."""
    for form in ("4", "L4", "l4", "line 4"):
        with tempfile.TemporaryDirectory() as root:
            p = _write(root, "c.py", "l1\nl2\nl3\nl4\nl5\n")
            res = tool_edit_file_impl(
                {
                    "path": "c.py",
                    "start_line": form,
                    "end_line": "5",
                    "new_text": "NEW",
                },
                root,
            )
            assert "must be a positive integer" not in res, f"rejected {form!r}"
            assert "NEW" in open(p, encoding="utf-8").read()


# ── 3b. Unanchored partial content must never clobber a file ──────────────


def test_short_file_is_not_clobbered_by_unanchored_partial_content():
    """A small file must get the same anchor protection as a large one.

    Regression: the guard read `len(existing_lines) > 2`, so any file of two
    lines or fewer was silently overwritten in full by partial content that
    named no anchor.
    """
    with tempfile.TemporaryDirectory() as root:
        original = "keep_me = 1\nkeep_me_too = 2\n"
        p = _write(root, "small.py", original)
        res = tool_edit_file_impl({"path": "small.py", "new_text": "ZZZ"}, root)
        assert open(p, encoding="utf-8").read() == original
        assert "rejected" in res.lower() or "failed" in res.lower()


def test_force_still_allows_intentional_whole_file_replacement():
    """force=True remains the documented escape hatch."""
    with tempfile.TemporaryDirectory() as root:
        p = _write(root, "small.py", "old_a = 1\nold_b = 2\n")
        tool_edit_file_impl(
            {"path": "small.py", "new_text": "brand_new = 1", "force": True}, root
        )
        assert "brand_new" in open(p, encoding="utf-8").read()


def test_end_line_without_start_line_is_reported():
    """end_line alone must not be silently discarded."""
    with tempfile.TemporaryDirectory() as root:
        original = "l1\nl2\nl3\nl4\nl5\n"
        p = _write(root, "c.py", original)
        res = tool_edit_file_impl(
            {"path": "c.py", "end_line": 3, "new_text": "NEW"}, root
        )
        # Either honoured or refused, but never a silent no-op success.
        if open(p, encoding="utf-8").read() == original:
            assert "failed" in res.lower() or "rejected" in res.lower()


# ── 4. A failed match must not cost minutes ───────────────────────────────


def test_failed_edit_on_large_file_is_fast():
    """A miss on a large file must fail fast.

    Regression: the similarity and character-subsequence tiers ran
    SequenceMatcher over every window and every character offset, taking
    ~41s on a 1.6k-line file and ~127s on a 7k-line file, then still failing.
    The RecoveryEngine retries, multiplying the stall.
    """
    with tempfile.TemporaryDirectory() as root:
        body = "".join(
            f"def fn_{i}():\n    value_{i} = {i}\n    return value_{i}\n\n"
            for i in range(500)
        )  # ~2000 lines
        p = _write(root, "big.py", body)

        stale = (
            "    def _method_that_does_not_exist(self):\n"
            '        self.log("absent")\n'
            "        return None\n"
            "    def _also_absent(self):\n"
            "        pass"
        )
        t0 = time.time()
        res = tool_edit_file_impl(
            {"path": "big.py", "old_text": stale, "new_text": "    pass"}, root
        )
        elapsed = time.time() - t0

        assert elapsed < 5.0, f"failed edit took {elapsed:.1f}s on a 2k-line file"
        assert "failed" in res.lower()
        assert open(p, encoding="utf-8").read() == body, "failed edit mutated the file"


def test_successful_fuzzy_edit_still_works_on_large_file():
    """Speeding up the miss path must not break the hit path."""
    with tempfile.TemporaryDirectory() as root:
        body = "".join(
            f"def fn_{i}():\n    value_{i} = {i}\n    return value_{i}\n\n"
            for i in range(500)
        )
        p = _write(root, "big.py", body)
        # Whitespace-drifted anchor: must still match via the fuzzy tier.
        tool_edit_file_impl(
            {
                "path": "big.py",
                "old_text": "def fn_250():\n      value_250 = 250\n      return value_250",
                "new_text": "def fn_250():\n    return 'patched'",
            },
            root,
        )
        result = open(p, encoding="utf-8").read()
        assert "patched" in result
        assert "def fn_249():" in result and "def fn_251():" in result
