import random

import structlog
from discord import Message, TextChannel

from discordgpt.client import client
from discordgpt.messaging.main import (
    is_mentioned,
    is_reply_to_my_message,
    try_to_send_message,
)
from discordgpt.openai_api.chatcompletion import (
    generate_ai_reaction,
    generate_ai_text_response,
)
from discordgpt.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


def early_exit_check(message: Message) -> bool:
    """Check if we should ignore this message and exit early without any additional processing or
    response generation.
    """
    # ignore messages from certain users (or other bots)
    if message.author.name in settings.IGNORE_SENDER_NAMES:
        logger.info(f"(ignoring message from {message.author.name})")
        return True

    if message.guild is None:
        # this should never happen for a text channel
        logger.warning("ignoring message in an unknown server")
        return True

    # make sure the bot has permissions to send messages in this channel
    if (guild_member := message.guild.get_member(client.user.id)) is None:  # type: ignore
        logger.error(f"couldn't get server user for {client.user}")
        return True
    bot_permissions = message.channel.permissions_for(guild_member)
    if not bot_permissions.send_messages:
        return True

    return False


async def handle_text_channel_message(message: Message):
    """Handle a message sent in a TextChannel."""
    channel: TextChannel = message.channel  # type: ignore

    # TESTING
    logger.info(f"@{message.author.name}: {message.content}")

    # checks to make sure we can/should even send a reply
    if early_exit_check(message):
        await maybe_add_reaction(message)
        return

    if is_mentioned(message):
        async with channel.typing():
            await send_channel_message_to(message)
            return

    if is_reply_to_my_message(message):
        async with channel.typing():
            await send_channel_message_to(message)
            return

    # chance to reply to any message in a channel
    if random.random() < settings.RANDOM_REPLY_CHANCE:
        logger.info(
            f"*** Randomly replying to `{message.author.name}` in `{channel.name}` ***"
        )
        await send_channel_message_to(message)


async def send_channel_message_to(message: Message) -> None:
    """Send a message in a text channel.

    Optionally add a reaction to the message first.
    """
    await generate_ai_reaction(message)

    async with message.channel.typing():
        response, generated_image_url = await generate_ai_text_response(message)

    if response is None:
        await maybe_add_reaction(message)
        return

    # whether to reply directly to this message or not
    if random.random() < 0.7:
        await try_to_send_message(message, response, generated_image_url, as_reply=True)
    else:
        await try_to_send_message(message, response, generated_image_url)


async def maybe_add_reaction(message: Message):
    if random.random() < settings.RANDOM_REACTION_CHANCE:
        await generate_ai_reaction(message)
