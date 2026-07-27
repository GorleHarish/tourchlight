from typing import Dict, Any
from context_manager.skills.base import BaseSkill, SkillResult


class MyCustomSkill(BaseSkill):
    """
    A template for creating your own custom tools for the agent.
    Place your logic inside the `execute` function and drop this file
    into the agent_skills/ directory — it will be auto-loaded at startup.
    """

    name = "my_custom_skill"
    description = "A template skill that demonstrates how to inject custom logic into the agent."
    icon = "✨"

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        message = input_data.get("message", "No message provided")

        # --- DO YOUR CUSTOM LOGIC HERE ---
        response_string = f"Custom skill executed successfully! You said: {message}"
        # ---------------------------------

        return SkillResult(success=True, output=response_string)

    def get_prompt(self) -> str:
        # BUG FIX: the old XML-style prompt format is not parsed by SkillRegistry
        # and was therefore invisible to the LLM.  Use the same format as all
        # built-in skills so the agent actually knows this tool exists.
        return (
            f"{self.icon} **{self.name}**: {self.description}\n"
            "  Input: {message: 'your message here'}"
        )
