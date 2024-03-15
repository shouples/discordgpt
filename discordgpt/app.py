import structlog
from discord import DMChannel, Message, RawReactionActionEvent, TextChannel

from discordgpt.client import client
from discordgpt.feedback import handle_reaction
from discordgpt.messaging.direct_message_channel import handle_direct_message
from discordgpt.messaging.text_channel import handle_text_channel_message
from discordgpt.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


def set_log_contextvars(message: Message) -> None:
    structlog.contextvars.bind_contextvars(
        author=message.author.name,
        channel_type=type(message.channel).__name__,
        message_url=message.jump_url,
    )
    if server_name := getattr(message.guild, "name", None):
        structlog.contextvars.bind_contextvars(server=server_name)
    if channel_name := getattr(message.channel, "name", None):
        structlog.contextvars.bind_contextvars(channel=channel_name)


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}")

    # used later for the initial system prompt to the OpenAI API so the model can "know"
    # when it's been mentioned or referenced in a message, rather than treating `<@!123456789>` as
    # some other user's id
    settings.CLIENT_USER_ID = client.user.id


@client.event
async def on_message(message: Message):
    if not client.user:
        # ignore messages before the bot is ready
        return
    if message.author == client.user:
        # ignore messages from self
        return

    set_log_contextvars(message)

    # check whether this was in a direct message or a text channel
    if isinstance(message.channel, DMChannel):
        await handle_direct_message(message)

    elif isinstance(message.channel, TextChannel):
        await handle_text_channel_message(message)

    else:
        logger.warning(
            f"ignoring message from unknown channel type: {type(message.channel)} --> {message=}"
        )


@client.event
async def on_raw_reaction_add(reaction_event: RawReactionActionEvent):
    if not reaction_event.member:
        return

    channel = client.get_channel(reaction_event.channel_id)
    if not isinstance(channel, (DMChannel, TextChannel)):
        logger.warning(
            f"ignoring reaction event from unknown channel type: {type(channel)}"
        )
        return

    message = await channel.fetch_message(reaction_event.message_id)
    if not message.author == client.user:
        # we get reaction add events for all messages, not just ones applied to our bot's messages
        return

    set_log_contextvars(message)
    logger.info(f"{reaction_event.emoji=} added to message")
    await handle_reaction(message, reaction_event)


client.run(settings.DISCORD_BOT_TOKEN.get_secret_value())
