"""
Tool syntax instructions for Torchlight.

Generates the appropriate tool calling syntax instructions based on context window size.
"""


def get_tool_syntax_for_context_size(max_tokens: int) -> str:
    """
    Return the tool calling syntax instructions appropriate for the model's context size.

    For small context models (<=5000 tokens): bare call syntax only
    For larger models: full <tool_call> syntax
    """
    if max_tokens <= 5000:
        return (
            "\nTool syntax: bare call at end of response, e.g.  READ_FILE(\"path\")\n"
            "Only ONE tool per response. Never put tools in backticks."
        )
    else:
        return (
            "\n\n## Tool Calling Syntax (CLI):\n"
            "Output EXACTLY this at the END of your response:\n"
            "<tool_call>\n"
            '{"name": "skill_name", "arguments": {"param": "value"}}\n'
            "</tool_call>\n"
            "Tool calls MUST be last. Only ONE tool call per turn.\n"
        )


def build_tool_syntax_prompt(
    max_tokens: int,
    tool_descriptions: str = "",
    include_skill_prompts: bool = True,
) -> str:
    """
    Build the complete tool syntax prompt for the system message.

    Args:
        max_tokens: Model's context window size
        tool_descriptions: Pre-generated tool descriptions block
        include_skill_prompts: Whether to include skill-specific prompts
    """
    small = max_tokens <= 5000

    if small:
        return get_tool_syntax_for_context_size(max_tokens)

    parts = [get_tool_syntax_for_context_size(max_tokens)]
    if tool_descriptions:
        parts.append(tool_descriptions)
    return "\n".join(parts)
