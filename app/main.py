import logging

from fastapi import FastAPI
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_serving_api")

app = FastAPI(title="Model Serving API")


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    max_new_tokens: int = Field(default=32, ge=1, le=128)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/generate")
async def generate(request: GenerateRequest) -> dict[str, str]:
    logger.info(
        "generation_request prompt_chars=%d max_new_tokens=%d",
        len(request.prompt),
        request.max_new_tokens,
    )
    return {
        "text": f"Placeholder: {request.prompt}",
        "model": "not-loaded-yet",
    }
