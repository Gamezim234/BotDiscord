from __future__ import annotations

import re
import unicodedata

import discord
from discord.ext import commands

import config


COMMAND_PREFIX = ".apelido"


async def delete_quietly(message: discord.Message):
    try:
        await message.delete()
    except discord.HTTPException:
        pass


async def send_temporary(*args, **kwargs):
    return


def can_use_nickname_command(member: discord.Member):
    return member.id == config.DEV_USER_ID


def normalize_name(value: str):
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", without_accents.lower())


def member_search_names(member: discord.Member):
    names = [
        member.name,
        member.display_name,
    ]

    global_name = getattr(member, "global_name", None)
    if global_name:
        names.append(global_name)

    return [name for name in names if name]


async def resolve_member(guild: discord.Guild, query: str):
    mention_match = re.fullmatch(r"<@!?(\d+)>", query)
    member_id = int(mention_match.group(1)) if mention_match else None

    if member_id is None and query.isdigit():
        member_id = int(query)

    if member_id is not None:
        member = guild.get_member(member_id)
        if member is not None:
            return member

        try:
            return await guild.fetch_member(member_id)
        except discord.NotFound:
            return None

    query_lower = query.lower()
    for member in guild.members:
        if member.name.lower() == query_lower or member.display_name.lower() == query_lower:
            return member

    normalized_query = normalize_name(query)
    if not normalized_query:
        return None

    exact_matches = []
    startswith_matches = []
    contains_matches = []

    for member in guild.members:
        normalized_names = [normalize_name(name) for name in member_search_names(member)]

        if normalized_query in normalized_names:
            exact_matches.append(member)
            continue

        if any(name.startswith(normalized_query) for name in normalized_names):
            startswith_matches.append(member)
            continue

        if any(normalized_query in name for name in normalized_names):
            contains_matches.append(member)

    for matches in (exact_matches, startswith_matches, contains_matches):
        if len(matches) == 1:
            return matches[0]

    return None


class Nickname(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        if not message.content.lower().startswith(f"{COMMAND_PREFIX} "):
            return

        await delete_quietly(message)

        if not isinstance(message.author, discord.Member) or not can_use_nickname_command(message.author):
            await send_temporary(message.channel, "Você não tem permissão para usar esse comando.")
            return

        content = message.content[len(COMMAND_PREFIX) :].strip()
        parts = content.split(maxsplit=1)
        if len(parts) < 2:
            await send_temporary(message.channel, "Use: `.apelido @usuario Novo Apelido`")
            return

        target_query, new_nickname = parts
        new_nickname = new_nickname.strip()

        if len(new_nickname) > 32:
            await send_temporary(message.channel, "O apelido precisa ter no máximo 32 caracteres.")
            return

        target = await resolve_member(message.guild, target_query)
        if target is None:
            await send_temporary(message.channel, "Não encontrei esse usuário. Use menção ou ID para garantir.")
            return

        bot_member = message.guild.me
        if bot_member is None:
            await send_temporary(message.channel, "Não consegui conferir minhas permissões.")
            return

        if not bot_member.guild_permissions.manage_nicknames:
            await send_temporary(message.channel, "Eu preciso da permissão Gerenciar Apelidos.")
            return

        if target.id != message.guild.owner_id and target.top_role >= bot_member.top_role:
            await send_temporary(message.channel, "Não consigo mudar o apelido dessa pessoa por causa da hierarquia de cargos.")
            return

        try:
            await target.edit(nick=new_nickname, reason=f"Apelido alterado por {message.author} ({message.author.id})")
        except discord.Forbidden:
            if target.id == message.guild.owner_id:
                await send_temporary(message.channel, "O Discord não permite que bot altere o apelido do dono do servidor.")
            else:
                await send_temporary(message.channel, "Não tenho permissão para mudar o apelido dessa pessoa.")
        except discord.HTTPException:
            await send_temporary(message.channel, "Não consegui mudar o apelido agora.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Nickname(bot))
