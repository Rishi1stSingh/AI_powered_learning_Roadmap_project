from pydantic import BaseModel, Field
class SkillInput(BaseModel):
    skill_id: str
    level: int = Field(ge=0, le=100)
