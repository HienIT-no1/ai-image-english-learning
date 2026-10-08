from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1,max_length=100)
    cefr_level: Literal['A1','A2','B1','B2']
    daily_goal: int = Field(ge=1,le=200)
    reminders_enabled: bool = False
    @field_validator('full_name')
    @classmethod
    def clean_name(cls,value):
        value=value.strip()
        if not value: raise ValueError('Name cannot be blank')
        return value

class ProfileResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    user_id: int
    username: str
    email: str
    full_name: str | None
    english_level: str | None
    cefr_level: str | None
    daily_goal: int | None
    reminders_enabled: bool
    onboarding_completed: bool
    current_streak: int | None
    longest_streak: int | None
