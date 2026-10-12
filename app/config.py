import os
from dataclasses import dataclass


def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class Settings:
    model_id: str
    max_input_tokens: int
    default_max_new_tokens: int
    max_new_tokens: int

    @classmethod
    def from_env(cls) -> "Settings":
        model_id = os.getenv("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct").strip()
        if not model_id:
            raise ValueError("MODEL_ID must not be empty")

        settings = cls(
            model_id=model_id,
            max_input_tokens=_positive_int_from_env("MAX_INPUT_TOKENS", 512),
            default_max_new_tokens=_positive_int_from_env(
                "DEFAULT_MAX_NEW_TOKENS", 32
            ),
            max_new_tokens=_positive_int_from_env("MAX_NEW_TOKENS", 128),
        )
        if settings.default_max_new_tokens > settings.max_new_tokens:
            raise ValueError(
                "DEFAULT_MAX_NEW_TOKENS cannot exceed MAX_NEW_TOKENS"
            )
        return settings


settings = Settings.from_env()
