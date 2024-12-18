import random
from dataclasses import dataclass

import structlog
from discord import Message, TextChannel

from src.client import client
from src.messaging.main import is_mentioned, is_reply_to_my_message, try_to_send_message
from src.openai_api.chatcompletion import (
    generate_ai_reaction,
    generate_ai_text_response,
)
from src.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class EarlyExitResult:
    should_exit: bool
    reason: str


def early_exit_check(message: Message) -> EarlyExitResult:
    """Check if we should ignore this message and exit early without any additional processing or
    response generation.
    """
    # ignore messages from certain users (or other bots)
    if message.author.name in settings.IGNORE_SENDER_NAMES:
        logger.info(f"(ignoring message from {message.author.name})")
        return EarlyExitResult(should_exit=True, reason="ignored user")

    if message.guild is None:
        # this should never happen for a text channel
        logger.warning("ignoring message in an unknown server")
        return EarlyExitResult(should_exit=True, reason="unknown server")

    # make sure the bot has permissions to send messages in this channel
    if (guild_member := message.guild.get_member(client.user.id)) is None:  # type: ignore
        logger.error(f"couldn't get server user for {client.user}")
        return EarlyExitResult(
            should_exit=True,
            reason="can't get server user for bot to check permissions",
        )

    bot_permissions = message.channel.permissions_for(guild_member)
    if not bot_permissions.send_messages:
        return EarlyExitResult(
            should_exit=True, reason="no send_messages permission for this channel"
        )

    return EarlyExitResult(should_exit=False, reason="")


async def handle_text_channel_message(message: Message):
    """Handle a message sent in a TextChannel."""
    channel: TextChannel = message.channel  # type: ignore

    check: EarlyExitResult = early_exit_check(message)
    # TESTING
    logger.info(
        f"@{message.author.name}: {message.content}",
        early_exit_check=check,
    )

    # checks to make sure we can/should even send a reply
    if check.should_exit:
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
    await maybe_add_reaction(message)

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
    chance = random.random()
    adding_reaction = chance < settings.RANDOM_REACTION_CHANCE
    logger.debug(
        f"react to message from {message.author.name}? {adding_reaction}",
        chance=chance,
        settings_chance=settings.RANDOM_REACTION_CHANCE,
    )
    if adding_reaction:
        await generate_ai_reaction(message)
