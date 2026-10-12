import logging
import time
from dataclasses import dataclass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.config import Settings


logger = logging.getLogger("model_serving_api")


class InputTooLongError(ValueError):
    def __init__(self, input_tokens: int, max_input_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.max_input_tokens = max_input_tokens
        super().__init__(
            f"Input contains {input_tokens} tokens; maximum is {max_input_tokens}"
        )


@dataclass(frozen=True)
class GenerationResult:
    text: str
    input_tokens: int


class ModelService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tokenizer = None
        self.model = None

    @property
    def loaded(self) -> bool:
        return self.tokenizer is not None and self.model is not None

    def load(self) -> None:
        logger.info("model_load_started model_id=%s", self.settings.model_id)
        started = time.perf_counter()

        self.tokenizer = AutoTokenizer.from_pretrained(self.settings.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.settings.model_id,
            torch_dtype=torch.float32,
        ).to("cpu")
        self.model.eval()

        logger.info(
            "model_load_complete model_load_seconds=%.3f",
            time.perf_counter() - started,
        )

    def generate(self, prompt: str, max_new_tokens: int) -> GenerationResult:
        if not self.loaded:
            raise RuntimeError("Model service has not finished loading")

        tokenizer = self.tokenizer
        model = self.model
        assert tokenizer is not None
        assert model is not None

        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(
            formatted_prompt,
            return_tensors="pt",
            add_special_tokens=False,
        )

        input_tokens = int(inputs["input_ids"].shape[1])
        if input_tokens > self.settings.max_input_tokens:
            raise InputTooLongError(
                input_tokens=input_tokens,
                max_input_tokens=self.settings.max_input_tokens,
            )

        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )

        new_token_ids = output_ids[0][input_tokens:]
        generated_text = tokenizer.decode(
            new_token_ids,
            skip_special_tokens=True,
        ).strip()
        return GenerationResult(text=generated_text, input_tokens=input_tokens)
