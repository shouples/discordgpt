Exploring the Discord API with [discord.py](https://discordpy.readthedocs.io/en/stable/intro.html) and the OpenAI API.

# Setup
- Create a Discord bot app here: https://discord.com/developers/applications/
- Create (or use an existing) [OpenAI API key](https://platform.openai.com/account/api-keys)
- Configure `.env` locally (example)
- Adjust `initial_prompt.md` as needed
- `poetry run python ./discordgpt/app.py`

# TODO items
- [ ] switch from ChatCompletion to the Assistants API; each server in its own thread with `channel:username` as the message `name` values
  - [ ] store `channel-username: threadid` mappings locally; if no thread ID exists, create thread and carry over last (up to) 10 messages in history
- [X] load attached images through https://platform.openai.com/docs/guides/vision
- [ ] add function calling for:
  - [X] image generation with https://platform.openai.com/docs/guides/images/usage?context=node
  - [ ] making external API requests
