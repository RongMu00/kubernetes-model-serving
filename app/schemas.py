from pydantic import BaseModel, Field

from app.config import settings


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    max_new_tokens: int = Field(
        default=settings.default_max_new_tokens,
        ge=1,
        le=settings.max_new_tokens,
    )


class GenerateResponse(BaseModel):
    text: str
    model: str


class HealthResponse(BaseModel):
    status: str
