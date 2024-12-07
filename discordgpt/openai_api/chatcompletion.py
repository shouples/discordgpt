import json
from datetime import datetime, timedelta
from typing import Literal

import structlog
from discord import Attachment, Message
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion, ChatCompletionMessage
from rich import print as rprint

from discordgpt.openai_api.function_calls import MODEL_FUNCTIONS
from discordgpt.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


async def get_message_history(message: Message, limit: int = 10) -> list[Message]:
    # get messages from the last hour up to the limit
    history_lookback: datetime = message.created_at - timedelta(hours=1)
    # get previous messages as context up to the current message (but at most `limit` messages)
    # and also add the current message in at the end
    messages = [
        msg
        async for msg in message.channel.history(
            # limit=limit,
            after=history_lookback,
            before=message.created_at,
        )
    ][-limit:]
    messages.append(message)
    # reverse the list so the oldest message is first
    # NOTE: this isn't necessary with `after` in the history call
    # messages.reverse()
    return messages


async def generate_context_messages(
    message: Message,
    check_for_image_attachments: bool = False,
) -> list[dict]:
    # TODO: this shouldn't be required once the Assistants API is used with thread IDs
    messages: list[Message] = await get_message_history(message)

    # add a starting prompt to the context to set the tone and instructions for the model
    starting_prompt = (
        f"You are user ID {settings.CLIENT_USER_ID}. {settings.OPENAI_STARTING_PROMPT}"
    )
    context_messages = [{"role": "system", "content": starting_prompt}]

    # add the previous messages to the context, with some print debugging
    debug_lines = []
    for other_message in messages:
        msg_time = other_message.created_at.strftime("%Y-%m-%d %H:%M:%S")

        if other_message.author.name.lower() == settings.DISCORD_BOT_NAME.lower():
            # sent by the bot
            message_dict = {
                "role": "assistant",
                "content": other_message.content,
            }
            debug_lines.append(
                f"{msg_time} | {message_dict['role']}: {message_dict['content']}"
            )
        else:
            # sent by a user
            message_dict = {
                "role": "user",
                "content": other_message.content,
                "name": other_message.author.name,
            }
            debug_lines.append(
                f"{msg_time} | {message_dict['role']} ({message_dict['name']}): {message_dict['content']}"
            )

        context_messages.append(message_dict)

        if check_for_image_attachments:
            # if any image attachments were included, send them to the vision model for a summary
            # before creating the final text response
            image_attachment_messages = await get_image_attachment_context(
                other_message
            )
            if image_attachment_messages:
                debug_lines.append(
                    f"{msg_time} | {image_attachment_messages[0]['role']}: {image_attachment_messages[0]['content']}"
                )
            context_messages = context_messages + image_attachment_messages

    # print the debug lines (not printing them within the loop since they might get mixed up with
    # the normal log lines)
    debug_lines_str = "\n".join(debug_lines)
    rprint(debug_lines_str)

    return context_messages


async def generate_ai_reaction(message: Message) -> None:
    context_messages = await generate_context_messages(
        message,
        check_for_image_attachments=True,
    )

    # get available server emojis if this isn't a DM
    server_emojis = {}
    if (server := message.guild) is not None:
        emoji_list = await server.fetch_emojis()
        server_emojis = {emoji.name: emoji for emoji in emoji_list}

    emoji_str = "emoji(s)."
    if server_emojis:
        emoji_str = f"the name(s) of one or more available server emoji(s): {list(server_emojis.keys())!r}\n\n...or emoji(s)."

    # temporary context for adding a reaction to the message, not to be used in the final response generation
    temp_reaction_context = context_messages[:]
    temp_reaction_context.append(
        {
            "role": "system",
            "content": f"NOT REQUIRED: Optionally add a reaction to the previous message with {emoji_str}",
        }
    )

    # determine whether to send a reaction or not
    function_call_resp = await get_function_call_response(
        message_context=temp_reaction_context,
        function_names=["generate_message_reaction", "auto"],
    )
    for function_call, function_parameters in function_call_resp:
        if function_call is generate_message_reaction:
            # add reaction to the message
            await function_call(
                message,
                function_parameters.get("emojis", []),
                server_emojis,
                function_parameters.get("reasoning"),
            )


async def generate_ai_text_response(message: Message) -> tuple[str | None, str]:
    context_messages: list[dict] = await generate_context_messages(
        message,
        check_for_image_attachments=True,
    )

    # possibly create an image based on previous messages (to include any attachmented images)
    created_image_url, created_image_messages = await create_image_context(
        message, context_messages
    )
    context_messages += created_image_messages

    # finally, generate the text response
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response: ChatCompletion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=context_messages,  # type: ignore
        user=message.author.name,
    )
    response_text = response.choices[0].message.content or ""
    logger.warning(f"sending response: {response_text!r}")
    return response_text, created_image_url


async def generate_image(
    prompt: str,
    user_name: str,
    style: Literal["vivid", "natural"] = "vivid",
) -> str | None:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.images.generate(
        model=settings.OPENAI_IMAGE_GEN_MODEL,
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        style=style,
        n=1,
        user=user_name,
    )
    image_url = response.data[0].url
    return image_url


async def get_image_attachment_context(message: Message) -> list[dict[str, str]]:
    if not message.attachments:
        return []

    attached_images = []
    for attachment_message in message.attachments:
        attachment_message: Attachment  # type: ignore
        if (content_type := getattr(attachment_message, "content_type", None)) is None:
            continue
        if not content_type.startswith("image/"):
            # skip non-image attachments
            continue
        if (image_url := getattr(attachment_message, "proxy_url", None)) is None:
            continue
        attached_images.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                }
            }
        )

    if attached_images:
        num_attached_images = len(attached_images)
        structlog.contextvars.bind_contextvars(num_attached_images=num_attached_images)
        logger.info(f"summarizing {num_attached_images} attached image(s)")

        image_count_str = "this image"
        if num_attached_images > 1:
            image_count_str = f"these {num_attached_images} images"
        vision_prompt = f"Give a simple, concise summary of what's in {image_count_str}"

        vision_message_context = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": vision_prompt},
                ]
                + attached_images,
            }
        ]

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_VISION_MODEL,
            messages=vision_message_context,  # type: ignore
            max_tokens=300,  # default is lower
        )
        image_summary_text = response.choices[0].message.content
        logger.warning(f"vision response: {image_summary_text!r}")

        structlog.contextvars.unbind_contextvars("num_attached_images")
        return [
            {
                "role": "system",
                "content": f"{message.author.name} uploaded {num_attached_images} image(s):\n{image_summary_text}",
            }
        ]

    return []


async def create_image_context(
    message: Message,
    message_context: list[dict],
) -> tuple[str, list[dict]]:
    """Determine whether or not to create an image based on the message history and current message
    content. If an image is created, return the image URL as well as a system message describing
    what was made.
    """
    image_url: str = ""
    image_context: list[dict] = []

    # don't use the full message history, because that will skew the prompting too much. just use
    # the last 1-2 messages, which will be the most relevant to the current message
    recent_message_context = message_context[-2:]
    image_gen_message_context = recent_message_context + [
        {
            "role": "system",
            "content": "Generate an image if the user is asking for an image to be created or edited. Otherwise, move on.",
        },
    ]

    image_function_calls = await get_function_call_response(
        image_gen_message_context,
        function_names=["generate_image", "auto"],
    )
    for function_call, function_parameters in image_function_calls:
        # make sure an image prompt was generated
        image_prompt: str = function_parameters.get("prompt", "")
        if not image_prompt:
            logger.warning(f"missing prompt in function call: {function_parameters!r}")
            return image_url, image_context

        image_style = function_parameters.get("style", "vivid")
        # function_call is really just `generate_image` here
        image_url = await function_call(
            prompt=image_prompt,
            style=image_style,
            user_name=message.author.name,  # type: ignore
        )
        if image_url:
            # let the model know an image was created successfully and include the generated prompt
            image_context = [
                {
                    "role": "system",
                    "content": f"The image was successfully generated with the following prompt: `{image_prompt!r}`\n\nYou will attach it in your response; DON'T ADD IMAGE MARKDOWN SYNTAX.",
                }
            ]
            return image_url, image_context

    return image_url, image_context


async def generate_message_reaction(
    message: Message,
    emojis: list[str],
    server_emojis: dict,
    reasoning: str = "",
):
    logger.info(f"adding reactions to message: {emojis!r} -> {reasoning=}")

    for emoji in emojis:
        # remove any newline characters or other whitespace
        emoji = emoji.strip()
        if len(emoji) > 1:
            # server emoji
            if (server_emoji := server_emojis.get(emoji)) is not None:
                await message.add_reaction(server_emoji)
            else:
                logger.warning(f"reaction {emoji!r} not found in server emojis")
        else:
            # standard emoji
            await message.add_reaction(emoji)


async def get_function_call_response(
    message_context: list[dict],
    function_names: list[str],
):
    if isinstance(function_names, str):
        function_names = [function_names]

    # allow model to choose between functions if multiple names were provided; otherwise force the
    # use of the single function name passed
    if len(function_names) != 1 or "auto" in function_names:
        tool_choice = "auto"
    else:
        tool_choice = {"type": "function", "function": {"name": function_names[0]}}  # type: ignore

    focused_model_functions = [
        func for func in MODEL_FUNCTIONS if func["function"]["name"] in function_names  # type: ignore
    ]
    structlog.contextvars.bind_contextvars(
        function_names=function_names,
        tool_choice=tool_choice,
        focused_model_functions=[
            f["function"]["name"] for f in focused_model_functions  # type: ignore
        ],
    )
    if not focused_model_functions:
        logger.warning("no focused model functions found for function names")
        return

    logger.debug("getting function call response...")
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response: ChatCompletion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=message_context,  # type: ignore
        tools=focused_model_functions,
        tool_choice=tool_choice,
    )
    response_message: ChatCompletionMessage = response.choices[0].message

    FUNCTION_CALLS = {
        "generate_image": generate_image,
        "generate_message_reaction": generate_message_reaction,
    }

    function_call_bundles = []
    tool_calls = response_message.tool_calls or []
    for tool_call in tool_calls:
        if (tool_func := tool_call.function) is None:
            continue
        logger.info(
            f"decided to call function: {tool_func.name!r} with args: {tool_func.arguments!r}"
        )
        if tool_func.name not in function_names:
            # hallucinated function name
            continue

        # parse the suggested args/kwargs for the function
        try:
            function_parameters = json.loads(tool_func.arguments)
        except json.JSONDecodeError:
            logger.warning(f"invalid JSON in function call: {tool_func.arguments!r}")
            continue

        tool_func_callable = FUNCTION_CALLS[tool_func.name]
        function_call_bundle = (tool_func_callable, function_parameters)
        function_call_bundles.append(function_call_bundle)
    if not function_call_bundles:
        logger.info("decided not to call any function(s)")

    structlog.contextvars.unbind_contextvars(
        "function_names", "tool_choice", "focused_model_functions"
    )
    return function_call_bundles
