"""
Utilities for parsing structured implementation plans and review questions.
"""

from __future__ import annotations
import re
from typing import Optional


def parse_plan_review_questions(text: str) -> list[dict]:
    """Parse structured review questions with radio/checkbox options from a markdown plan or final answer.

    Returns a list of dicts:
        [
            {
                "question": "1. Game Controls",
                "options": [
                    "(Recommended) Arrow Keys + WASD: Standard dual-layout controls",
                    "Arrow Keys Only: Minimal controls",
                ],
                "is_multi_select": False,
                "allow_custom_input": True,
            },
            ...
        ]
    """
    if not text or not isinstance(text, str):
        return []

    # Find User Review Required / Open Questions section if present
    section_match = re.search(
        r"(?:^|\n)#{2,6}\s*(?:User Review Required|Open Questions)[^\n]*\n([\s\S]*?)(?=(?:\n#{1,4}\s+(?:Proposed Changes|Verification|Architecture|Implementation)|\Z))",
        text,
        re.IGNORECASE,
    )
    search_scope = section_match.group(1) if section_match else text

    questions: list[dict] = []
    # Match headers like ### 1. Question Title [Single Choice / Radio] or **1. Question Title**
    blocks = re.split(r"(?:\n|^)(?:###+|\*\*|\d+\.\s*[\*\#]*)\s*", search_scope)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        header_line = lines[0].strip("#* ")
        # Check if this line looks like a question or has input type
        is_multi = bool(re.search(r"multi[- ]select|checkbox", block, re.IGNORECASE))
        has_radio = bool(re.search(r"single[- ]choice|radio", block, re.IGNORECASE))

        # Extract options lines with markers: - (•), - ( ), - [ ], - [x], - 1., 1.
        options: list[str] = []
        for line in lines[1:]:
            opt_match = re.match(
                r"^[-*•]\s*(?:\([•xX\s*]\)|\[[•xX\s*]\]|\d+\.|\([0-9]+\))\s*(.*)$",
                line,
            )
            if opt_match:
                opt_text = opt_match.group(1).strip()
                if opt_text and not opt_text.lower().startswith("custom input"):
                    options.append(opt_text)
                elif opt_text and opt_text.lower().startswith("custom input"):
                    # Custom input marker found
                    pass
            elif re.match(r"^[-*•]\s+(.+)$", line) and (has_radio or is_multi or "(Recommended)" in line):
                clean_opt = re.sub(r"^[-*•]\s+", "", line).strip()
                if not clean_opt.lower().startswith("custom input"):
                    options.append(clean_opt)

        if options and (has_radio or is_multi or any("(Recommended)" in o for o in options) or "(•)" in block or "( )" in block or "[ ]" in block):
            q_clean = re.sub(r"\[(Single Choice|Radio|Multi[- ]Select|Checkbox)[^\]]*\]", "", header_line, flags=re.IGNORECASE).strip(" :*#-")
            questions.append(
                {
                    "question": q_clean or header_line,
                    "options": options,
                    "is_multi_select": is_multi,
                    "allow_custom_input": True,
                }
            )

    return questions
