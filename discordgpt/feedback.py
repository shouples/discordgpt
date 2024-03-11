import structlog
from discord import Message, RawReactionActionEvent

from discordgpt.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def handle_reaction(
    message: Message, reaction_event: RawReactionActionEvent
) -> None:
    structlog.contextvars.bind_contextvars(message_url=message.jump_url)

    if reaction_event.emoji.name in settings.POSITIVE_FEEDBACK_EMOJIS:
        return await on_positive_feedback(message)

    if reaction_event.emoji.name in settings.NEGATIVE_FEEDBACK_EMOJIS:
        return await on_negative_feedback(message)


async def on_positive_feedback(message: Message) -> None:
    """Handle a positive feedback message."""
    logger.info("positive feedback received! 😁")


async def on_negative_feedback(message: Message) -> None:
    """Handle a negative feedback message."""
    logger.info("negative feedback received 😢")
