"""Anthropic Messages API provider."""

import logging

from anthropic import AsyncAnthropic

from services.ai.providers.base import AIProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    """Provider backed by the Anthropic Messages API."""

    def _setup(self) -> None:
        if not self.api_key:
            logger.warning("Anthropic API key is not set. AI replies will be unavailable.")
            return

        try:
            self.client = AsyncAnthropic(api_key=self.api_key)
            self._is_configured = True
            logger.info("Anthropic client successfully configured.")
        except Exception as e:
            logger.error("Failed to configure Anthropic client: %s", e, exc_info=True)

    async def generate_reply(
        self,
        message_text: str,
        system_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str | None:
        if not self._is_configured or not self.client:
            logger.error("Attempted to generate reply but Anthropic client is not configured.")
            return None

        try:
            logger.info("Sending request to Anthropic model %s...", self.model_name)
            messages: list[dict[str, str]] = [
                {"role": turn["role"], "content": turn["content"]}
                for turn in chat_history or []
            ]
            messages.append({"role": "user", "content": self._user_prompt(message_text)})

            response = await self.client.messages.create(
                model=self.model_name,
                system=system_prompt,
                messages=messages,
                temperature=0.7,
                max_tokens=300,
            )
            text_blocks = [
                block.text.strip()
                for block in response.content
                if getattr(block, "type", None) == "text" and getattr(block, "text", None)
            ]
            if text_blocks:
                logger.info("Successfully generated reply from Anthropic.")
                return "\n".join(text_blocks).strip()

            logger.warning("Anthropic returned an empty response.")
            return None
        except Exception as e:
            logger.error("Error calling Anthropic API: %s", e, exc_info=True)
            return None
