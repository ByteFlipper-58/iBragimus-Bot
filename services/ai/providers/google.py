"""Google Gemini provider."""

import logging

from google import genai
from google.genai import types

from services.ai.providers.base import AIProvider

logger = logging.getLogger(__name__)


class GoogleProvider(AIProvider):
    """Provider backed by the Google Gemini API."""

    def _setup(self) -> None:
        if not self.api_key:
            logger.warning("Gemini API key is not set. AI replies will be unavailable.")
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            self._is_configured = True
            logger.info("Google Gemini client successfully configured using google-genai SDK.")
        except Exception as e:
            logger.error("Failed to configure Google Gemini client: %s", e, exc_info=True)

    async def generate_reply(
        self,
        message_text: str,
        system_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str | None:
        if not self._is_configured or not self.client:
            logger.error("Attempted to generate reply but Google Gemini client is not configured.")
            return None

        try:
            safety_settings = [
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
            ]

            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=300,
                system_instruction=system_prompt,
                safety_settings=safety_settings,
            )

            # Gemini expects the "model" role instead of "assistant".
            contents: list[types.Content] = []
            for turn in chat_history or []:
                role = "model" if turn["role"] == "assistant" else "user"
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=turn["content"])])
                )
            contents.append(
                types.Content(role="user", parts=[types.Part(text=self._user_prompt(message_text))])
            )

            logger.info("Sending request to Google Gemini model %s...", self.model_name)
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            if response and response.text:
                logger.info("Successfully generated reply from Google Gemini.")
                return response.text.strip()

            logger.warning("Google Gemini returned an empty response.")
            return None
        except Exception as e:
            logger.error("Error calling Google Gemini API: %s", e, exc_info=True)
            return None
