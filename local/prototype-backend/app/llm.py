from __future__ import annotations

import json
import re

from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to a .env file in the project root."
            )
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def _complete(model: str, messages: list[dict], json_mode: bool) -> str:
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = get_client().chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The model returned an empty response.")
    return content


def chat(messages: list[dict], json_mode: bool = False, use_fallback_first: bool = False) -> str:
    primary = settings.openai_fallback_model if use_fallback_first else settings.openai_model
    fallback = settings.openai_model if use_fallback_first else settings.openai_fallback_model
    try:
        return _complete(primary, messages, json_mode)
    except Exception:
        if fallback and fallback != primary:
            return _complete(fallback, messages, json_mode)
        raise


def parse_json_object(text: str) -> dict:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


def parse_markdown_text(text: str) -> str:
    """Strip one outer ```markdown fence; keep code blocks inside the document intact."""
    text = text.strip()
    outer = re.fullmatch(r"```(?:markdown|md)?[ \t]*\n([\s\S]*?)\n?```", text)
    return outer.group(1).strip() if outer else text


def parse_yaml_text(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:ya?ml)?\s*([\s\S]*?)```", text)
    if fenced:
        return fenced.group(1).strip()
    return text
