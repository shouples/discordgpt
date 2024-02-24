Exploring the Discord API with [discord.py](https://discordpy.readthedocs.io/en/stable/intro.html) and the OpenAI API.

This is mainly used for toying around with a bot user in a single server. I haven't tried anything with multi-server configs yet, but I don't imagine they'd work well for the time being.

# Setup
- Create a Discord bot app here: https://discord.com/developers/applications/
- Create (or use an existing) [OpenAI API key](https://platform.openai.com/account/api-keys)
- Configure `.env` locally ([example](https://github.com/shouples/discordgpt/blob/main/.env.example))
- Adjust `initial_prompt.md` as needed ([example](https://github.com/shouples/discordgpt/blob/main/initial_prompt.md))
- `poetry run python ./discordgpt/app.py`

# TODO items
- [ ] switch from ChatCompletion to the Assistants API; each server in its own thread with `channel:username` as the message `name` values
  - [ ] store `channel-username: threadid` mappings locally; if no thread ID exists, create thread and carry over last (up to) 10 messages in history
- [X] summarize user-attached images via https://platform.openai.com/docs/guides/vision
- [ ] add function calling for:
  - [X] image generation with https://platform.openai.com/docs/guides/images/usage?context=node
  - [X] adding reactions to messages, either with unicode emojis or with server-specific reactions
  - [ ] making external API requests / web browsing
- [ ] handle multi-server bots and settings

# Longer-term fun goals
- [ ] explore usage with local models capable of using similar function calling methods
- [ ] voice channel support
  - [ ] load user audio https://platform.openai.com/docs/guides/speech-to-text
  - [ ] emit bot audio https://platform.openai.com/docs/guides/text-to-speech
