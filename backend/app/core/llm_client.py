import os
import json
from typing import AsyncGenerator
from openai import OpenAI, AsyncOpenAI
from app.core.config import settings

_client: OpenAI | None = None
_async_client: AsyncOpenAI | None = None


def _get_llm_api_key() -> str:
    if settings.llm_api_key not in ("sk-your-api-key", ""):
        return settings.llm_api_key
    return os.environ.get("DEEPSEEK_API_KEY") or settings.llm_api_key


def _get_llm_base_url() -> str:
    if settings.llm_base_url not in ("https://api.openai.com/v1", ""):
        return settings.llm_base_url
    return os.environ.get("DEEPSEEK_BASE_URL") or settings.llm_base_url


def _get_llm_model() -> str:
    if settings.llm_model not in ("gpt-4o-mini", ""):
        return settings.llm_model
    return os.environ.get("DEEPSEEK_MODEL") or settings.llm_model


def get_llm_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=_get_llm_api_key(),
            base_url=_get_llm_base_url(),
        )
    return _client


def get_async_llm_client() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(
            api_key=_get_llm_api_key(),
            base_url=_get_llm_base_url(),
        )
    return _async_client


def build_prefix_cache_request(prefix_content: str, main_content: str) -> list[dict]:
    return [
        {"role": "system", "content": prefix_content},
        {"role": "user", "content": "PREFIX_CACHE_WARMUP"},
    ]


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    response_format: dict | None = None,
) -> str:
    """Non-streaming chat completion. Uses sync client in thread to avoid blocking."""
    import asyncio

    kwargs = dict(
        model=model or _get_llm_model(),
        messages=messages,
        max_tokens=max_tokens or settings.llm_max_tokens,
        temperature=temperature or settings.llm_temperature,
    )
    if response_format:
        kwargs["response_format"] = response_format

    def _sync_call() -> str:
        client = get_llm_client()
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    return await asyncio.to_thread(_sync_call)


async def chat_completion_stream(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> AsyncGenerator[str, None]:
    """Streaming chat completion using AsyncOpenAI."""
    client = get_async_llm_client()
    stream = await client.chat.completions.create(
        model=model or _get_llm_model(),
        messages=messages,
        max_tokens=max_tokens or settings.llm_max_tokens,
        temperature=temperature or settings.llm_temperature,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content


async def cache_warmup_completion(messages: list[dict]) -> dict:
    """Send request with max_tokens=1 to trigger prefix cache establishment."""
    import asyncio

    def _sync_call() -> dict:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=_get_llm_model(),
            messages=messages,
            max_tokens=1,
            temperature=0,
        )
        return {
            "id": response.id,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }

    return await asyncio.to_thread(_sync_call)
