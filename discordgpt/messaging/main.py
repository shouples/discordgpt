import re
from io import BytesIO

import aiohttp
import structlog
from discord import File, Message
from discord.errors import Forbidden

from discordgpt.client import client
from discordgpt.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def try_to_send_message(
    message: Message,
    reply_content: str,
    attached_image_url: str,
    as_reply: bool = False,
):
    """Try to send a message in the current channel, either as a reply or a new message.
    If an attached image URL is provided, it will be downloaded and sent as an attachment.
    Any errors will be caught and logged.
    """
    async with message.channel.typing():
        msg_send_op = message.reply if as_reply else message.channel.send
        params = {"content": reply_content}

        image_attachment: File | None = await make_image_attachment(attached_image_url)
        if image_attachment:
            params["file"] = image_attachment  # type: ignore

    try:
        await msg_send_op(**params)  # type: ignore
    except Forbidden:
        logger.error(
            f"missing permissions to send messages in `{message.channel.name}`"  # type: ignore
        )
    except Exception as e:
        logger.error(f"error sending message: {e}")


async def make_image_attachment(image_url: str) -> File | None:
    """Download an image from a URL and return it as a `discord.File` object."""
    if not image_url:
        return None

    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            if resp.status != 200:
                logger.warning(
                    f"Could not download image file to attach to message: {resp}"
                )
                return None
            data = BytesIO(await resp.read())
            return File(data, filename="image.png")


def is_mentioned(message: Message) -> bool:
    """Check if the bot is mentioned in a message, either by name or as a direct mention."""
    mentioned_directly = client.user in message.mentions

    # this should never be an empty string after the bot is initialized / logged in
    client_username: str = getattr(client.user, "name", "").lower()
    if not client_username:
        logger.error("client username is empty")
        return False

    msg_content: str = getattr(message, "content", "").lower()
    name_in_content = (
        client_username in msg_content or settings.DISCORD_BOT_NAME in msg_content
    )
    return mentioned_directly or name_in_content


def is_reply_to_my_message(message: Message) -> bool:
    """Check if a message is a reply to a message sent by the bot."""
    if (ref := message.reference) is None:
        # not a reply
        return False

    if not isinstance(ref.resolved, Message):
        # could be referencing a deleted message
        return False

    return ref.resolved.author == client.user


def is_only_url(text: str) -> bool:
    """Determine if a text string is only a URL."""
    url_pattern = r"^https?://[^\s]+$"
    return bool(re.match(url_pattern, text))
