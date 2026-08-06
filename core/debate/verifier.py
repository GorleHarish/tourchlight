"""
DebateVerifier implementation: orchestrates adversarial critique and refinement loops.
"""

from dataclasses import dataclass, field
import json
import re
from typing import Optional, TYPE_CHECKING

from ..api.base import InferenceParams, LLMClient
from ..tools.classification import AUTO, CONFIRM, REVIEW, classify_tool
from .prompts import (
    CRITIC_SYSTEM_PROMPT,
    REFINER_SYSTEM_PROMPT,
    PLAN_CRITIC_PROMPT_TEMPLATE,
    CODE_CRITIC_PROMPT_TEMPLATE,
)

if TYPE_CHECKING:
    pass


@dataclass
class CritiqueResult:
    """Structured result of an adversarial critique step."""
    has_flaws: bool = False
    flaws: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    raw_response: str = ""


class DebateVerifier:
    """
    Orchestrates multi-turn debate (Proposer -> Critic -> Refiner) to elevate
    output quality on 7B models.
    """

    def __init__(self, llm_client: LLMClient, enabled: bool = True):
        self.client = llm_client
        self.enabled = enabled

    def should_debate(self, tool_name: Optional[str] = None, phase: str = "code") -> bool:
        """
        Determine whether debate/critique should be run.

        Bypasses debate for low-risk AUTO tools (e.g. READ_FILE, GREP) to save context and speed.
        Triggers debate for high-risk tools (WRITE_FILE, EDIT_FILE, RUN_COMMAND) or planning phases.
        """
        if not self.enabled:
            return False

        if phase == "plan":
            return True

        if tool_name:
            tier = classify_tool(tool_name)
            if tier in (CONFIRM, REVIEW):
                return True
            return False

        # Default for code/troubleshoot phases when tool_name is unknown
        return phase in ("code", "troubleshoot")

    async def critique(
        self, proposal: str, task_context: str, phase: str = "code"
    ) -> CritiqueResult:
        """
        Execute an adversarial critique pass using InferenceParams.for_critic().
        """
        if phase == "plan":
            user_content = PLAN_CRITIC_PROMPT_TEMPLATE.format(
                task=task_context, proposed_plan=proposal
            )
        else:
            user_content = CODE_CRITIC_PROMPT_TEMPLATE.format(
                task=task_context, proposed_output=proposal
            )

        # Pre-critique: check if Python code blocks have actual syntax/compile errors
        import ast
        code_blocks = re.findall(r'```python\n(.*?)```', proposal, re.DOTALL)
        compile_errors = []
        for block in code_blocks:
            try:
                ast.parse(block)
            except SyntaxError as e:
                compile_errors.append(f"L{e.lineno}: {e.msg}")

        if compile_errors:
            user_content += f"\n\nConfirmed compile errors: {compile_errors}"
        elif code_blocks:
            user_content += "\n\nNote: Code compiles cleanly without syntax errors. Focus on semantic/logic issues only."

        messages = [
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        critic_params = InferenceParams.for_critic()
        response_text = await self.client.chat(messages, params=critic_params)

        return self._parse_critique_json(response_text)

    async def refine(
        self, proposal: str, critique: CritiqueResult, task_context: str
    ) -> str:
        """
        Synthesize refined output incorporating valid critiques using InferenceParams.for_refine().
        """
        if not critique.has_flaws:
            return proposal

        critique_summary = {
            "flaws": critique.flaws,
            "recommendations": critique.recommendations,
        }

        user_content = f"""Task Context: {task_context}

Original Proposal:
{proposal}

Peer Review Critiques:
{json.dumps(critique_summary, indent=2)}

Synthesize the revised and improved final response/tool-call directly."""

        messages = [
            {"role": "system", "content": REFINER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        refine_params = InferenceParams.for_refine()
        return await self.client.chat(messages, params=refine_params)

    async def verify_and_refine(
        self,
        proposal: str,
        task_context: str,
        tool_name: Optional[str] = None,
        phase: str = "code",
    ) -> tuple[str, CritiqueResult]:
        """
        Full debate flow: evaluate should_debate, execute critique, and refine if flaws exist.

        Returns:
            (final_output, critique_result)
        """
        if not self.should_debate(tool_name=tool_name, phase=phase):
            return proposal, CritiqueResult(has_flaws=False)

        critique_res = await self.critique(proposal, task_context, phase=phase)

        if critique_res.has_flaws and (critique_res.flaws or critique_res.recommendations):
            refined_output = await self.refine(proposal, critique_res, task_context)
            return refined_output, critique_res

        return proposal, critique_res

    def _parse_critique_json(self, text: str) -> CritiqueResult:
        """Helper to extract JSON payload or XML tags from LLM response."""
        result = CritiqueResult(raw_response=text)

        # Try XML tag extraction first (more robust for 7B models)
        flaw_matches = re.findall(r'<flaw>(.*?)</flaw>', text, re.DOTALL)
        rec_matches = re.findall(r'<recommendation>(.*?)</recommendation>', text, re.DOTALL)
        if flaw_matches or rec_matches:
            result.has_flaws = bool(flaw_matches)
            result.flaws = [f.strip() for f in flaw_matches]
            result.recommendations = [r.strip() for r in rec_matches]
            return result

        # Strip markdown ```json ... ``` codeblocks if present
        clean_text = text.strip()
        if "```" in clean_text:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1)
            else:
                # Try finding first '{' and last '}'
                start = clean_text.find("{")
                end = clean_text.rfind("}")
                if start != -1 and end != -1:
                    clean_text = clean_text[start : end + 1]

        try:
            data = json.loads(clean_text)
            result.has_flaws = bool(data.get("has_flaws", False))
            result.flaws = data.get("flaws", [])
            result.recommendations = data.get("recommendations", [])
        except (json.JSONDecodeError, AttributeError):
            # If JSON parsing fails, check for specific multi-word indicators of flaws
            lower_text = text.lower()
            flaw_indicators = [
                "syntax error", "logic flaw", "missing import", "undefined variable",
                "type mismatch", "incorrect return", "broken reference", "critical flaw"
            ]
            if sum(1 for ind in flaw_indicators if ind in lower_text) >= 1:
                result.has_flaws = True
                result.flaws = [text.strip()]

        return result
