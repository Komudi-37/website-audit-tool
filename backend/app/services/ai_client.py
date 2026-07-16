"""
AI Client — wraps OpenRouter via the OpenAI-compatible SDK.

Usage:
    from app.services.ai_client import ai_client
    text = await ai_client.generate("Summarise these findings: ...")
"""

import logging
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError

from app.core.config import settings

logger = logging.getLogger("audit_tool.ai_client")


class AIClient:
    """
    Reusable async client for OpenRouter.

    Initialises the underlying OpenAI-compatible HTTP client once and
    exposes a single public method: generate().
    """

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            timeout=120,
            default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "AI Website Audit Tool",
    },
            
        )
        self._model: str = settings.OPENROUTER_MODEL
        logger.info(
            "AIClient initialised — provider=openrouter, model=%s",
            self._model,
        )

    async def generate(self, prompt: str) -> str:
        """
        Send a prompt to OpenRouter and return the generated text.

        Args:
            prompt: The full prompt string to send.

        Returns:
            The model's response as a plain string.

        Raises:
            RuntimeError: If the API call fails or returns no content.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not configured. "
                "Set it in your .env file."
            )

        logger.debug(
            "Sending prompt to OpenRouter (model=%s, chars=%d)",
            self._model,
            len(prompt),
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=0.2,
                messages=[
                    {
        "role": "system",
        "content": (
            "You are an expert AI Website Audit Assistant. "
            "Always produce professional, concise, technically accurate website audit reports. "
            "Return valid JSON whenever requested."
        ),
    },
                    {"role": "user", "content": prompt},
                ],
            )
        except RateLimitError as exc:
            logger.error("OpenRouter rate limit exceeded: %s", exc)
            raise RuntimeError(
                "AI service rate limit exceeded. Please try again later."
            ) from exc
        except APIConnectionError as exc:
            logger.error("OpenRouter connection error: %s", exc)
            raise RuntimeError(
                "Could not connect to the AI service. "
                "Check your network and try again."
            ) from exc
        except APIError as exc:
            logger.error("OpenRouter API error (status=%s): %s", exc.status_code, exc)
            raise RuntimeError(
                f"AI service returned an error (HTTP {exc.status_code}). "
                "Please try again."
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error calling OpenRouter: %s", exc)
            raise RuntimeError(
                f"Unexpected error contacting the AI service: {exc}"
            ) from exc

        try:
            text = response.choices[0].message.content
        except (IndexError, AttributeError) as exc:
            logger.error("Unexpected OpenRouter response shape: %s", response)
            raise RuntimeError(
                "AI service returned an unexpected response format."
            ) from exc

        if not text or not text.strip():
            raise RuntimeError("AI service returned an empty response.")

        logger.debug(
            "Received response from OpenRouter (chars=%d)",
            len(text),
        )
        return text.strip()


# Module-level singleton — import this everywhere
ai_client = AIClient()