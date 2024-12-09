from discord import Client, Intents


def create_client() -> Client:
    intents = Intents.default()
    intents.message_content = True
    return Client(intents=intents)


client: Client = create_client()
