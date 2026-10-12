import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.model_service import InputTooLongError, ModelService
from app.schemas import GenerateRequest, GenerateResponse, HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_serving_api")
service = ModelService(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "application_starting model_id=%s max_input_tokens=%d "
        "default_max_new_tokens=%d max_new_tokens=%d",
        settings.model_id,
        settings.max_input_tokens,
        settings.default_max_new_tokens,
        settings.max_new_tokens,
    )
    service.load()
    yield


app = FastAPI(title="Model Serving API", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    started = time.perf_counter()
    try:
        result = service.generate(request.prompt, request.max_new_tokens)
    except InputTooLongError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    logger.info(
        "generation_complete input_tokens=%d max_new_tokens=%d latency_ms=%.1f",
        result.input_tokens,
        request.max_new_tokens,
        (time.perf_counter() - started) * 1000,
    )
    return GenerateResponse(text=result.text, model=settings.model_id)
