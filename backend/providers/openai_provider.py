"""
NutriAI - OpenAI-Compatible Provider (OpenRouter)
Supports: any model on openrouter.ai (GPT-4o, Claude, Gemini, Llama, etc.)
Author: Senior AI Engineer
"""

import os
import json
import httpx
from typing import List, Dict, Optional
from fastapi import HTTPException


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL       = "openai/gpt-4o-mini"        # cheapest smart model
FALLBACK_MODEL      = "mistralai/mistral-7b-instruct"  # free fallback
REQUEST_TIMEOUT     = 60.0   # seconds


# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER CLASS
# ══════════════════════════════════════════════════════════════════════════════

class OpenAIProvider:
    """
    OpenRouter-compatible provider using raw httpx (no SDK dependency).
    Works with any OpenAI-compatible API endpoint.
    """

    def __init__(
        self,
        api_key:  Optional[str] = None,
        model:    str = DEFAULT_MODEL,
        base_url: str = OPENROUTER_BASE_URL,
    ):
        self.api_key  = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model    = model
        self.base_url = base_url.rstrip("/")

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")

        # ── Shared headers for every request ──
        self._headers = {
            "Authorization":  f"Bearer {self.api_key}",
            "Content-Type":   "application/json",
            "HTTP-Referer":   "https://nutriai.app",   # shown on openrouter dashboard
            "X-Title":        "NutriAI",
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE: core HTTP call
    # ──────────────────────────────────────────────────────────────────────────

    async def _call(self, payload: dict) -> dict:
        """
        Send POST to /chat/completions and return parsed JSON.
        Raises HTTPException on any failure.
        """
        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            try:
                response = await client.post(url, headers=self._headers, json=payload)
                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail="OpenRouter request timed out"
                )
            except httpx.HTTPStatusError as e:
                # Try to extract OpenRouter error message
                try:
                    error_detail = e.response.json().get("error", {}).get("message", str(e))
                except Exception:
                    error_detail = str(e)
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"OpenRouter error: {error_detail}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error calling OpenRouter: {str(e)}"
                )

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE: extract text from response
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_text(response: dict) -> str:
        try:
            return response["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected OpenRouter response format: {str(e)}"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: single turn (system + user)
    # Used by: /diet/generate
    # ──────────────────────────────────────────────────────────────────────────

    async def chat(
        self,
        system_prompt: str,
        user_prompt:   str,
        temperature:   float = 0.2,
        max_tokens:    int   = 8000,   # 15-day plan needs room
        model:         Optional[str] = None,
    ) -> str:
        """
        Single-turn call: system + user → assistant reply.
        Returns raw text string.
        """
        payload = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }

        response = await self._call(payload)
        return self._extract_text(response)

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: multi-turn with history
    # Used by: /chat (conversation memory)
    # ──────────────────────────────────────────────────────────────────────────

    async def chat_with_history(
        self,
        messages:    List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens:  int   = 1024,
        model:       Optional[str] = None,
    ) -> str:
        """
        Multi-turn call: full conversation history → next assistant reply.
        messages format: [ {"role": "user/assistant/system", "content": "..."} ]
        Returns raw text string.
        """
        payload = {
            "model":       model or self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }

        response = await self._call(payload)
        return self._extract_text(response)

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: list available models (useful for debugging/admin)
    # ──────────────────────────────────────────────────────────────────────────

    async def list_models(self) -> List[str]:
        """
        Fetch all available models from OpenRouter.
        Returns list of model IDs.
        """
        url = f"{self.base_url}/models"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=self._headers)
                response.raise_for_status()
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Could not fetch models: {str(e)}")

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: switch model at runtime
    # ──────────────────────────────────────────────────────────────────────────

    def set_model(self, model: str) -> None:
        """Hot-swap the model without reinstantiating the provider."""
        self.model = model