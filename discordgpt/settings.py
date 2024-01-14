from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DISCORDGPT_TOKEN: SecretStr = SecretStr("")
    DISCORDGPT_NAME: str = ""

    OPENAI_API_KEY: str = ""

    OPENAI_MODEL: str = ""
    OPENAI_STARTING_PROMPT: str = ""

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings():
    return Settings()
