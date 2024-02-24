import os
from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DISCORD_BOT_TOKEN: SecretStr = SecretStr("")
    DISCORD_BOT_NAME: str = ""
    CLIENT_USER_ID: str = ""

    OPENAI_API_KEY: str = ""

    OPENAI_MODEL: str = ""
    OPENAI_STARTING_PROMPT: str | list[str] = ""

    # required for summarizing image attachments
    OPENAI_VISION_MODEL: str = ""
    # required for generating images and adding to message responses
    OPENAI_IMAGE_GEN_MODEL: str = ""

    # required for using the Assistants API
    # TODO: use this instead of managing history manually
    OPENAI_ASSISTANT_ID: str = ""

    # if this is greater than 0.0, for any server this bot is in, there is a chance that the bot
    # will reply to any message in a TextChannel
    RANDOM_REPLY_CHANCE: float = 0.05
    # ...or react to a message with an emoji or server reaction
    RANDOM_REACTION_CHANCE: float = 0.05

    # comma-separated list of usernames to ignore messages from
    IGNORE_SENDER_NAMES: str | list[str] = ""

    # comma-separated list of usernames to ignore messages from
    IGNORE_SENDER_NAMES: str | list[str] = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("IGNORE_SENDER_NAMES", mode="before")
    @classmethod
    def validate_IGNORE_SENDER_NAMES(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            # don't replace spaces so we don't accidentally mess up a username
            v = [name.strip() for name in v.split(",")]
        return v

    @field_validator("OPENAI_STARTING_PROMPT", mode="before")
    @classmethod
    def validate_OPENAI_STARTING_PROMPT(cls, v: str | list[str]) -> str:
        # multi-line strings don't load well from .env files, so we load directly from a separate
        # file instead
        return open("initial_prompt.md").read().strip()


@lru_cache
def get_settings():
    return Settings()
