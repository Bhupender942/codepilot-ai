"""Tests for the patch engine (app/services/patch_engine.py)."""

from __future__ import annotations

import pytest

from app.services.patch_engine import PatchEngine, get_patch_engine
from app.utils.diff_utils import extract_target_file, validate_diff


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

VALID_DIFF = """\
--- a/src/foo.py
+++ b/src/foo.py
@@ -1,2 +1,3 @@
 def foo():
-    return 1
+    return 2
+    # improved
"""

DIFF_IN_FENCE = f"Some explanation.\n\n```diff\n{VALID_DIFF}```\n"


# ===========================================================================
# parse_unified_diff / validate_diff (diff_utils helpers used by PatchEngine)
# ===========================================================================


def test_parse_valid_unified_diff():
    """A well-formed diff with ---/+++/@@ lines is parsed into hunks."""
    from app.utils.diff_utils import parse_unified_diff

    hunks = parse_unified_diff(VALID_DIFF)
    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk["old_file"] == "src/foo.py"
    assert hunk["new_file"] == "src/foo.py"
    assert hunk["old_start"] == 1
    assert hunk["new_start"] == 1
    assert any(line.startswith("+") for line in hunk["lines"])
    assert any(line.startswith("-") for line in hunk["lines"])


def test_validate_valid_diff():
    """validate_diff returns True for a well-formed unified diff."""
    assert validate_diff(VALID_DIFF) is True


def test_validate_invalid_diff():
    """Random text (no diff markers) → validate_diff returns False."""
    assert validate_diff("this is just a sentence") is False


def test_validate_empty_string():
    """Empty string → validate_diff returns False."""
    assert validate_diff("") is False


def test_extract_target_file():
    """extract_target_file returns the path after +++ b/ prefix."""
    target = extract_target_file(VALID_DIFF)
    assert target == "src/foo.py"


def test_extract_target_file_no_b_prefix():
    """extract_target_file strips the b/ prefix from the +++ line."""
    diff = "--- a/lib/util.py\n+++ b/lib/util.py\n@@ -1 +1 @@\n x\n"
    assert extract_target_file(diff) == "lib/util.py"


# ===========================================================================
# PatchEngine.parse_llm_output
# ===========================================================================


def test_parse_code_block_fallback():
    """LLM output with ```diff...``` block is correctly extracted."""
    engine = PatchEngine()
    result = engine.parse_llm_output(DIFF_IN_FENCE)

    assert result["raw_diff"] != ""
    assert validate_diff(result["raw_diff"]) is True


def test_parse_llm_output_extracts_target_file():
    """parse_llm_output sets target_file from the diff's +++ header."""
    engine = PatchEngine()
    result = engine.parse_llm_output(VALID_DIFF)

    assert result["target_file"] == "src/foo.py"


def test_parse_llm_output_extracts_explanation():
    """Explanatory text before the diff block is returned as explanation."""
    llm_text = "This patch fixes the off-by-one error.\n\n" + VALID_DIFF
    engine = PatchEngine()
    result = engine.parse_llm_output(llm_text)

    assert "off-by-one" in result["explanation"]


def test_parse_llm_output_extracts_unit_test():
    """A ```python ... ``` block containing def test_ is extracted as unit_test."""
    test_block = "```python\ndef test_fix():\n    assert foo() == 2\n```"
    llm_text = VALID_DIFF + "\n\n" + test_block
    engine = PatchEngine()
    result = engine.parse_llm_output(llm_text)

    assert "def test_" in result["unit_test"]


def test_parse_llm_output_no_unit_test():
    """Output without a python test block returns empty unit_test string."""
    engine = PatchEngine()
    result = engine.parse_llm_output(VALID_DIFF)

    assert result["unit_test"] == ""


def test_parse_llm_output_hunks_structure():
    """Each hunk in the result has 'header' and 'lines' keys."""
    engine = PatchEngine()
    result = engine.parse_llm_output(VALID_DIFF)

    for hunk in result["hunks"]:
        assert "header" in hunk
        assert "lines" in hunk
        assert isinstance(hunk["lines"], list)


# ===========================================================================
# PatchEngine.validate_diff
# ===========================================================================


def test_engine_validate_diff_delegates():
    """PatchEngine.validate_diff returns the same result as the util function."""
    engine = PatchEngine()
    assert engine.validate_diff(VALID_DIFF) is True
    assert engine.validate_diff("not a diff") is False


# ===========================================================================
# Malformed / edge-case diffs
# ===========================================================================


def test_malformed_diff_no_exception():
    """Partial / malformed diff input does not raise an exception."""
    engine = PatchEngine()
    partial = "--- a/foo.py\n"  # no +++ or @@ lines

    result = engine.parse_llm_output(partial)
    assert isinstance(result, dict)
    assert "raw_diff" in result
    assert "hunks" in result


def test_no_diff_in_output():
    """LLM output with no recognisable diff returns safe defaults."""
    engine = PatchEngine()
    result = engine.parse_llm_output("I could not find the issue in the code.")

    assert result["raw_diff"] == ""
    assert result["hunks"] == []
    assert result["target_file"] == ""


# ===========================================================================
# PatchEngine.create_patch_prompt
# ===========================================================================


def test_create_patch_prompt_contains_issue():
    """The generated prompt includes the issue description."""
    engine = PatchEngine()
    chunks = [
        {
            "file_path": "src/auth.py",
            "start_line": 10,
            "end_line": 20,
            "language": "python",
            "text": "def login(user, pwd): pass",
        }
    ]
    prompt = engine.create_patch_prompt(chunks, "login does not validate passwords")
    assert "login does not validate passwords" in prompt
    assert "src/auth.py" in prompt


def test_create_patch_prompt_includes_diff_format_instruction():
    """The prompt instructs the LLM to produce a unified diff."""
    engine = PatchEngine()
    prompt = engine.create_patch_prompt([], "fix the bug")
    assert "unified diff" in prompt.lower() or "---" in prompt or "@@ " in prompt


# ===========================================================================
# Singleton
# ===========================================================================


def test_get_patch_engine_singleton():
    """get_patch_engine() returns the same instance across calls."""
    import app.services.patch_engine as pe_module

    pe_module._patch_engine_instance = None  # reset
    a = get_patch_engine()
    b = get_patch_engine()
    assert a is b
