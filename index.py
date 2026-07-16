import os

import discord
from discord.ext import commands

from utils import load_env


load_env()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()

    if bot.user is None:
        print("Bot conectado, mas nao foi possivel ler o usuario.")
        return

    print(f"Bot conectado como {bot.user} (ID: {bot.user.id})")


async def load_extensions():
    await bot.load_extension("cogs.idea_form")
    await bot.load_extension("cogs.nickname")
    await bot.load_extension("cogs.tickets")


async def main():
    if not DISCORD_TOKEN or DISCORD_TOKEN == "cole_seu_token_aqui":
        raise RuntimeError("Coloque o token do bot no arquivo .env.")

    async with bot:
        await load_extensions()
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
