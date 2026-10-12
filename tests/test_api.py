import logging

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, service
from app.model_service import GenerationResult, InputTooLongError


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(service, "load", lambda: None)
    with TestClient(app) as test_client:
        yield test_client


def test_lifespan_loads_model(monkeypatch: pytest.MonkeyPatch) -> None:
    load_calls = 0

    def mock_load() -> None:
        nonlocal load_calls
        load_calls += 1

    monkeypatch.setattr(service, "load", mock_load)
    with TestClient(app):
        pass

    assert load_calls == 1


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MAX_INPUT_TOKENS", "0"),
        ("DEFAULT_MAX_NEW_TOKENS", "-1"),
        ("MAX_NEW_TOKENS", "not-an-integer"),
    ],
)
def test_settings_reject_invalid_positive_integers(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError):
        Settings.from_env()


def test_settings_reject_default_above_maximum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEFAULT_MAX_NEW_TOKENS", "129")
    monkeypatch.setenv("MAX_NEW_TOKENS", "128")

    with pytest.raises(
        ValueError,
        match="DEFAULT_MAX_NEW_TOKENS cannot exceed MAX_NEW_TOKENS",
    ):
        Settings.from_env()


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_returns_model_output(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    prompt = "PRIVATE_PROMPT_MUST_NOT_APPEAR_IN_LOGS"

    def mock_generate(request_prompt: str, max_new_tokens: int) -> GenerationResult:
        assert request_prompt == prompt
        assert max_new_tokens == 17
        return GenerationResult(text="Mock model response", input_tokens=9)

    monkeypatch.setattr(service, "generate", mock_generate)
    caplog.set_level(logging.INFO, logger="model_serving_api")

    response = client.post(
        "/v1/generate",
        json={"prompt": prompt, "max_new_tokens": 17},
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "Mock model response",
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
    }
    assert "input_tokens=9" in caplog.text
    assert "max_new_tokens=17" in caplog.text
    assert prompt not in caplog.text
    assert "Mock model response" not in caplog.text


@pytest.mark.parametrize(
    "body",
    [
        {"prompt": "", "max_new_tokens": 32},
        {"prompt": "Hello", "max_new_tokens": 0},
        {"prompt": "Hello", "max_new_tokens": 129},
    ],
)
def test_invalid_request_returns_422(client: TestClient, body: dict) -> None:
    response = client.post("/v1/generate", json=body)

    assert response.status_code == 422


def test_tokenized_input_too_large_returns_413(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate(prompt: str, max_new_tokens: int) -> GenerationResult:
        raise InputTooLongError(input_tokens=513, max_input_tokens=512)

    monkeypatch.setattr(service, "generate", mock_generate)

    response = client.post(
        "/v1/generate",
        json={"prompt": "A structurally valid but token-heavy prompt"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Input contains 513 tokens; maximum is 512"
    }
