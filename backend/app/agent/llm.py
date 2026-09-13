from __future__ import annotations
import json
import re
from functools import lru_cache
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_llm():
    if not settings.deepseek_api_key:
        return None
    kwargs = {
        "model": settings.deepseek_model,
        "temperature": settings.llm_temperature,
        "api_key": settings.deepseek_api_key,
        "max_retries": 2,
    }
    # ChatDeepSeek 官方配置通常不需要显式 base_url；保留环境变量主要给自定义部署扩展。
    return ChatDeepSeek(**kwargs)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError(f"模型没有返回合法 JSON: {text[:300]}")
        return json.loads(match.group(0))


def ask_json(system: str, user: str) -> dict[str, Any] | None:
    llm = get_llm()
    if llm is None:
        return None
    msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    return _extract_json(content)
