from context_manager.skills.base import BaseSkill, SkillResult
from typing import Dict, Any

class ReproSkill(BaseSkill):
    name = "repro_skill"
    description = "Test skill for reload verification"
    icon = "🧪"
    
    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        return SkillResult(success=True, output="Skill Version 1")
