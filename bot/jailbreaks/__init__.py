# -*- coding: utf-8 -*-
"""
PAYOMBØYZ MULTI-MODEL JAILBREAK ENGINE
Integrates and tunes jailbreak specifications from Lerning/jailbreaks-main
for DeepSeek, Gemini, Qwen/ThaiLLM, and BluezyGPT/GPT models.
"""

from typing import Optional
from bot.jailbreaks.deepseek import get_deepseek_jailbreak
from bot.jailbreaks.gemini import get_gemini_jailbreak
from bot.jailbreaks.qwen import get_qwen_jailbreak
from bot.jailbreaks.gpt import get_gpt_jailbreak


def get_model_jailbreak(
    provider_or_model: str,
    mode: str = "script_professor",
    user_name: str = "User",
    base_prompt: Optional[str] = None
) -> str:
    """
    Returns the battle-tested, model-specific jailbreak prompt tuned for PAYOMBØYZ work:
    - DeepSeek (V3/R1/OpenRouter)
    - Gemini / Gemma (Google GenAI)
    - Qwen / ThaiLLM (Alibaba/ThaiLLM)
    - GPT / BluezyGPT (OpenAI/Developer Platform)
    """
    key = (provider_or_model or "").lower().strip()

    if any(k in key for k in ("deepseek", "openrouter")):
        return get_deepseek_jailbreak(mode=mode, user_name=user_name)

    if any(k in key for k in ("gemini", "gemma", "google")):
        return get_gemini_jailbreak(mode=mode, user_name=user_name)

    if any(k in key for k in ("qwen", "thaillm", "pathumma")):
        return get_qwen_jailbreak(mode=mode, user_name=user_name)

    if any(k in key for k in ("bluezy", "gpt", "openai")):
        return get_gpt_jailbreak(mode=mode, user_name=user_name)

    # Default to DeepSeek specification as universal foundation
    return get_deepseek_jailbreak(mode=mode, user_name=user_name)
