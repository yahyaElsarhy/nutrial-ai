"""
NutriAI - Groq Provider
Groq offers ultra-fast LLM inference (LPU hardware).
Models: llama-3.3-70b, llama-3.1-8b, mixtral-8x7b, gemma2-9b
Author: Senior AI Engineer
"""

import os
import httpx
from typing import List, Dict, Optional
from fastapi import HTTPException


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

GROQ_BASE_URL    = "https://api.groq.com/openai/v1"
DEFAULT_MODEL    = "llama-3.3-70b-versatile"   # best quality on Groq
FAST_MODEL       = "llama-3.1-8b-instant"       # ultra-fast for chat
REQUEST_TIMEOUT  = 60.0


# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER CLASS
# ══════════════════════════════════════════════════════════════════════════════

class GroqProvider:
    """
    Groq LPU inference provider.
    Uses OpenAI-compatible /chat/completions endpoint via raw httpx.
    """

    def __init__(
        self,
        api_key:  Optional[str] = None,
        model:    str = DEFAULT_MODEL,
        base_url: str = GROQ_BASE_URL,
    ):
        self.api_key  = api_key or os.getenv("GROQ_API_KEY")
        self.model    = model
        self.base_url = base_url.rstrip("/")

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set")

        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE: core HTTP call
    # ──────────────────────────────────────────────────────────────────────────

    async def _call(self, payload: dict) -> dict:
        """
        POST to Groq /chat/completions.
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
                    detail="Groq request timed out — try a smaller model like llama-3.1-8b-instant"
                )
            except httpx.HTTPStatusError as e:
                try:
                    error_body  = e.response.json()
                    error_msg   = error_body.get("error", {}).get("message", str(e))
                    error_type  = error_body.get("error", {}).get("type", "")

                    # ── Groq-specific rate limit ──
                    if e.response.status_code == 429:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Groq rate limit reached: {error_msg}"
                        )

                    # ── Context length exceeded ──
                    if "context_length" in error_type or "tokens" in error_msg.lower():
                        raise HTTPException(
                            status_code=400,
                            detail="Input too long for this model. Try summarizing the history."
                        )

                except HTTPException:
                    raise
                except Exception:
                    error_msg = str(e)

                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Groq API error: {error_msg}"
                )

            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error calling Groq: {str(e)}"
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
                detail=f"Unexpected Groq response format: {str(e)}"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE: get token usage for monitoring
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_usage(response: dict) -> dict:
        usage = response.get("usage", {})
        return {
            "prompt_tokens":     usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens":      usage.get("total_tokens", 0),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: single turn (system + user)
    # Used by: /diet/generate
    # ──────────────────────────────────────────────────────────────────────────

    async def chat(
        self,
        system_prompt: str,
        user_prompt:   str,
        temperature:   float = 0.2,
        max_tokens:    int   = 8000,
        model:         Optional[str] = None,
    ) -> str:
        """
        Single-turn: system + user → assistant reply.
        Uses DEFAULT_MODEL (70b) for best quality on diet generation.
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
        Multi-turn: full conversation history → next assistant reply.
        Uses FAST_MODEL (8b) for low-latency chat responses.
        Returns raw text string.
        """
        payload = {
            "model":       model or FAST_MODEL,   # 8b is fast enough for chat
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }

        response = await self._call(payload)
        return self._extract_text(response)

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: chat with usage stats (for cost monitoring)
    # ──────────────────────────────────────────────────────────────────────────

    async def chat_with_usage(
        self,
        system_prompt: str,
        user_prompt:   str,
        temperature:   float = 0.2,
        max_tokens:    int   = 8000,
    ) -> dict:
        """
        Same as chat() but also returns token usage.
        Useful for monitoring & cost tracking.
        Returns: { "text": str, "usage": { prompt_tokens, completion_tokens, total_tokens } }
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }

        response = await self._call(payload)
        return {
            "text":  self._extract_text(response),
            "usage": self._extract_usage(response),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: switch model at runtime
    # ──────────────────────────────────────────────────────────────────────────

    def set_model(self, model: str) -> None:
        """Hot-swap the model without reinstantiating the provider."""
        self.model = model

    def use_fast_model(self) -> None:
        """Switch to the fast 8b model (lower latency, less quality)."""
        self.model = FAST_MODEL

    def use_quality_model(self) -> None:
        """Switch to the 70b model (higher quality, slightly slower)."""
        self.model = DEFAULT_MODEL