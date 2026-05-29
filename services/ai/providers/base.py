"""Common base class shared by all AI providers."""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Common async interface for text reply generation."""

    def __init__(self, api_key: str | None, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self._is_configured = False
        self.client = None
        self._setup()

    @abstractmethod
    def _setup(self) -> None:
        """Initialize the provider client. Must set ``self._is_configured``."""

    @abstractmethod
    async def generate_reply(
        self,
        message_text: str,
        system_prompt: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str | None:
        """Generate a reply for an incoming message.

        ``chat_history`` is an ordered list of prior turns, each a dict with
        ``role`` (``"user"``/``"assistant"``) and ``content`` keys. When
        provided, it is sent to the model so replies stay consistent with the
        conversation.
        """

    @staticmethod
    def _user_prompt(message_text: str) -> str:
        """Wrap the raw user text in the persona-establishing instruction."""
        return (
            f'Пользователь написал: "{message_text}". '
            "Сформулируй краткий, естественный ответ от моего имени."
        )
