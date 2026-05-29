"""OpenAI Responses API provider."""

import logging

from openai import AsyncOpenAI

from services.ai.providers.base import AIProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """Provider backed by the OpenAI Responses API."""

    def _setup(self) -> None:
        if not self.api_key:
            logger.warning("OpenAI API key is not set. AI replies will be unavailable.")
            return

        try:
            self.client = AsyncOpenAI(api_key=self.api_key)
            self._is_configured = True
            logger.info("OpenAI client successfully configured.")
        except Exception as e:
            logger.error("Failed to configure OpenAI client: %s", e, exc_info=True)

    async def generate_reply(
        self,
        message_text: str,
        system_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str | None:
        if not self._is_configured or not self.client:
            logger.error("Attempted to generate reply but OpenAI client is not configured.")
            return None

        try:
            logger.info("Sending request to OpenAI model %s...", self.model_name)
            conversation: list[dict[str, str]] = [
                {"role": turn["role"], "content": turn["content"]}
                for turn in chat_history or []
            ]
            conversation.append({"role": "user", "content": self._user_prompt(message_text)})

            response = await self.client.responses.create(
                model=self.model_name,
                instructions=system_prompt,
                input=conversation,
                temperature=0.7,
                max_output_tokens=300,
            )
            reply = getattr(response, "output_text", None)
            if reply:
                logger.info("Successfully generated reply from OpenAI.")
                return reply.strip()

            logger.warning("OpenAI returned an empty response.")
            return None
        except Exception as e:
            logger.error("Error calling OpenAI API: %s", e, exc_info=True)
            return None
