import random

import structlog
from discord import DMChannel, Message

from discordgpt.messaging.main import try_to_send_message
from discordgpt.openai_api.chatcompletion import (
    generate_ai_reaction,
    generate_ai_text_response,
)
from discordgpt.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def handle_direct_message(message: Message):
    """Handle a message sent directly to the bot via DMChannel."""
    if not isinstance(message.channel, DMChannel):
        return

    channel: DMChannel = message.channel

    async with channel.typing():
        # check how many others are in the conversation
        recipients = getattr(channel, "recipients", [channel.recipient])
        if len(recipients) > 1:
            # TODO: handle group messages
            logger.error(
                f"ignoring group message from {message.author}: {message.content}",
                reason="not implemented",
            )
            return

        # 1:1 message, always respond
        await send_direct_message_to(message)


async def send_direct_message_to(message: Message) -> None:
    """Send a message to a user who has sent a direct message to the bot.
    Optionally add a reaction to the message first.
    """
    await generate_ai_reaction(message)

    async with message.channel.typing():
        response, generated_image_url = await generate_ai_text_response(message)

    if not response:
        return

    # don't reply directly to this message, just send it back in the conversation
    await try_to_send_message(message, response, generated_image_url)
