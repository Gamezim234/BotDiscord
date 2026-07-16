from __future__ import annotations

import asyncio
import io
import re
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands

import config


TICKET_PANEL_TITLE = "<:ticket_3:1509547413558263848> __ CENTRA DE ATENDIMENTO__ <:ticket_3:1509547413558263848>"
TICKET_EMOJI = "<:ticket_3:1509547413558263848>"
SUPPORT_EMOJI = "<:paper_2:1509549547544907887>"
PARTNERSHIP_EMOJI = "<:parceria:1509547629938212894>"
TAG_EMOJI = "<:light_1:1509549706437726348>"
REPORT_EMOJI = "<:alerta:1509547240216199258>"
RECRUITMENT_EMOJI = "<:xp:1509652127587369131>"
SELECT_EMOJI = "<:psiu:1509547518269067384>"
SEARCH_EMOJI = "<:lupa:1509549664762855515>"
CLAIM_EMOJI = "📜"
CLOSE_EMOJI = "🔒"
TRANSCRIPT_DIR = Path(__file__).resolve().parent.parent / "transcripts"

TICKET_FORM_FIELDS = {
    "support": [
        ("Qual sua Dúvida?", "Digite Aqui"),
    ],
    "partnership": [
        ("Qual o Nome da sua Clã ou Loja/Etc...", "Digite Aqui"),
        ("Motivo da Parceria/Aliança", "Digite Aqui"),
        ("Por que devemos aceitar a aliança", "Digite Aqui"),
    ],
    "tag": [
        ("Qual Cargo Você Possui / Deseja Ter?", "Digite Aqui"),
    ],
    "report": [
        ("Username do Reportado? Mine e Discord", "Digite Aqui"),
        ("Envie as Prova(s). (Youtube ou Medal)", "Mande a Prova Aqui"),
    ],
    "recruitment": [
        ("Qual seu Nickname (No Minecraft)", "Digite Aqui"),
        ("Qual seu Ponto Forte?", "Digite Aqui"),
    ],
}

TICKET_TYPES = {
    "support": {
        "emoji": SUPPORT_EMOJI,
        "label": "Suporte / Dúvidas",
        "slug": "suporte",
        "style": discord.ButtonStyle.blurple,
        "description": "Dúvidas Gerais (Dentro do Servidor).",
    },
    "partnership": {
        "emoji": PARTNERSHIP_EMOJI,
        "label": "Parceria/Aliança",
        "slug": "parceria",
        "style": discord.ButtonStyle.red,
        "description": "Pedir / Solicitar uma Parceria ou Aliança com sua Loja ou Clã.",
    },
    "tag": {
        "emoji": TAG_EMOJI,
        "label": "Solicitar Tag & VIPs",
        "slug": "tag-vip",
        "style": discord.ButtonStyle.green,
        "description": "Pedir / Solicitar uma Tag dentro do Servidor do Discord.",
    },
    "report": {
        "emoji": REPORT_EMOJI,
        "label": "Denunciar um Membro",
        "slug": "denuncia",
        "style": discord.ButtonStyle.gray,
        "description": "Reportar um Jogador que esteja Desrespeitando as Regras do Servidor.",
    },
    "recruitment": {
        "emoji": RECRUITMENT_EMOJI,
        "label": "Recrutamento",
        "slug": "recrutamento",
        "style": discord.ButtonStyle.green,
        "description": "Ser Recrutado para ser Membro iniciante, Membro Oficial etc.",
    },
}

ALL_TICKET_ROLE_IDS = [
    1509538270609019090,
    1509538608304885802,
    1509539078138237078,
    1512666227737231420,
    1512666810108084284,
    1509538667893620927,
    1509538765235032094,
]

GENERAL_TICKET_ROLE_IDS = [
    1509539210884026519,
    1509540402254843904,
    1509540580282339449,
]

RECRUITMENT_ONLY_ROLE_IDS = [
    1509540653179338833,
    1509541035444011151,
]


def clean_channel_name(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    return text.strip("-")[:90] or "ticket"


def get_ticket_staff_role_ids(ticket_id):
    role_ids = list(ALL_TICKET_ROLE_IDS)

    if ticket_id in {"support", "tag", "report"}:
        role_ids.extend(GENERAL_TICKET_ROLE_IDS)

    if ticket_id == "recruitment":
        role_ids.extend(RECRUITMENT_ONLY_ROLE_IDS)

    return role_ids


def user_has_any_role(user, role_ids):
    return any(role.id in role_ids for role in user.roles)


def parse_ticket_topic(topic):
    data = {}
    if not topic:
        return data

    for part in topic.split(";"):
        if "=" not in part:
            continue

        key, value = part.split("=", 1)
        data[key.strip()] = value.strip()

    return data


def build_ticket_topic(owner_id, ticket_id, claimed_by=None, opened_at=None):
    return (
        f"ticket_owner={owner_id};"
        f"ticket_type={ticket_id};"
        f"ticket_claimed_by={claimed_by or ''};"
        f"ticket_opened_at={opened_at or datetime.now().isoformat(timespec='seconds')}"
    )


def format_datetime(value):
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y às %H:%M")

    if not value:
        return "Não informado"

    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y às %H:%M")
    except ValueError:
        return value


def build_ticket_open_embed(user, ticket_id, ticket_data, answers, opened_at):
    staff_mentions = " ".join(f"<@&{role_id}>" for role_id in get_ticket_staff_role_ids(ticket_id))
    hidden_staff_mentions = f"||{staff_mentions}||"
    embed = discord.Embed(
        title="Ticket Aberto",
        description=(
            f"{user.mention} abriu seu Ticket de **{ticket_data['label']}**.\n\n"
            "• Os tickets podem ser atendidos em no máximo **3h**.\n\n"
            "• Depois das **19:00** não atendemos mais tickets. "
            "Depois desse período, podemos demorar mais para atender.\n\n"
            f"**Tipo:** {ticket_data['emoji']} {ticket_data['label']}\n"
            f"**Criado em:** {format_datetime(opened_at)}\n\n"
            f"**Equipe que pode reivindicar:**\n{hidden_staff_mentions}"
        ),
        color=discord.Color.green(),
    )

    for label, value in answers:
        embed.add_field(name=label, value=value[:1024] or "Não informado.", inline=False)

    embed.set_footer(text="Ticket King /close")
    return embed


def build_ticket_open_log_embed(ticket_channel, user, ticket_data, opened_at):
    embed = discord.Embed(title="Ticket Aberto", color=discord.Color.green())
    embed.add_field(name="Nome do Ticket", value=ticket_channel.mention, inline=True)
    embed.add_field(name="Criado Por", value=user.mention, inline=True)
    embed.add_field(name="Data de Abertura", value=format_datetime(opened_at), inline=True)
    embed.add_field(name="Tipo de Ticket", value=f"{ticket_data['emoji']} {ticket_data['label']}", inline=False)
    return embed


async def get_ticket_log_channel(bot):
    channel = bot.get_channel(config.TICKET_LOG_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(config.TICKET_LOG_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        return None

    return channel


async def send_ticket_open_log(bot, ticket_channel, user, ticket_data, opened_at):
    log_channel = await get_ticket_log_channel(bot)
    if log_channel is None:
        return

    await log_channel.send(embed=build_ticket_open_log_embed(ticket_channel, user, ticket_data, opened_at))


async def build_transcript(channel):
    lines = []
    async for message in channel.history(limit=None, oldest_first=True):
        created_at = message.created_at.strftime("%d/%m/%Y %H:%M:%S")
        content = message.content or ""
        attachments = " ".join(attachment.url for attachment in message.attachments)
        line = f"[{created_at}] {message.author}: {content}"
        if attachments:
            line += f" | Anexos: {attachments}"
        lines.append(line)

    if not lines:
        lines.append("Nenhuma mensagem encontrada.")

    return "\n".join(lines).encode("utf-8")


def save_transcript(message_id, transcript):
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    transcript_path = TRANSCRIPT_DIR / f"{message_id}.txt"
    transcript_path.write_bytes(transcript)
    return transcript_path


def is_staff_member(member):
    role_ids = set(ALL_TICKET_ROLE_IDS + GENERAL_TICKET_ROLE_IDS + RECRUITMENT_ONLY_ROLE_IDS)
    return user_has_any_role(member, role_ids)


async def count_staff_messages(channel):
    counts = {}
    async for message in channel.history(limit=None):
        if message.author.bot or not isinstance(message.author, discord.Member):
            continue

        if not is_staff_member(message.author):
            continue

        counts[message.author] = counts.get(message.author, 0) + 1

    return counts


async def send_ticket_close_log(interaction, closed_by):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        return

    topic_data = parse_ticket_topic(channel.topic)
    ticket_id = topic_data.get("ticket_type")
    if ticket_id is None:
        ticket_data = {"emoji": TICKET_EMOJI, "label": "Ticket"}
    else:
        ticket_data = TICKET_TYPES.get(ticket_id, {"emoji": TICKET_EMOJI, "label": "Ticket"})
    owner_id = topic_data.get("ticket_owner")
    claimed_by = topic_data.get("ticket_claimed_by")
    opened_at = topic_data.get("ticket_opened_at")
    closed_at = datetime.now()

    log_channel = await get_ticket_log_channel(interaction.client)
    if log_channel is None:
        return

    transcript = await build_transcript(channel)
    staff_counts = await count_staff_messages(channel)

    embed = discord.Embed(title="Ticket Fechado", color=discord.Color.red())
    embed.add_field(name="Nome do Ticket", value=channel.mention, inline=True)
    embed.add_field(name="Autor do Ticket", value=f"<@{owner_id}>" if owner_id else "Não informado", inline=True)
    embed.add_field(name="Fechado por", value=closed_by.mention, inline=True)
    embed.add_field(name="Reivindicado Por", value=f"<@{claimed_by}>" if claimed_by else "-", inline=True)
    embed.add_field(name="Data de Abertura", value=format_datetime(opened_at), inline=True)
    embed.add_field(name="Data de encerramento", value=format_datetime(closed_at), inline=True)
    embed.add_field(name="Tipo de Ticket", value=f"{ticket_data['emoji']} {ticket_data['label']}", inline=False)
    embed.add_field(name="Motivo para fechar o Ticket", value="-", inline=False)

    if staff_counts:
        count_lines = [f"[ {count} ] - {member.mention}" for member, count in staff_counts.items()]
        embed.add_field(name="Contagem de Mensagens Staff", value="\n".join(count_lines)[:1024], inline=False)
    else:
        embed.add_field(name="Contagem de Mensagens Staff", value="-", inline=False)

    log_message = await log_channel.send(embed=embed, view=TranscriptButtonView())
    save_transcript(log_message.id, transcript)


def build_ticket_embed():
    description = (
        f"#  {TICKET_EMOJI} __ CENTRA DE ATENDIMENTO__ {TICKET_EMOJI} \n"
        f"{SEARCH_EMOJI}: Escolha abaixo o tipo de atendimento que deseja abrir.\n"
        " Abra um ticket para:\n"
        f"- {SUPPORT_EMOJI} **Suporte / Dúvidas**\n"
        f"- {PARTNERSHIP_EMOJI} Solicitar **Parceria**\n"
        f"- {TAG_EMOJI} Socilitar TAGs & **VIPs**\n"
        f"- {REPORT_EMOJI} **Denunciar um Membro**\n"
        f"- {RECRUITMENT_EMOJI} **Recrutamento**\n"
        f"- {SELECT_EMOJI} **Selecione uma categoria no menu para abrir seu ticket.**{TICKET_EMOJI}\n"
        "———————————————————————————————————\n"
        '** "Ah, Mas Para que Server Cada Coisa?🤓"** \n\n'
        '- **"Suporte / Dúvidas"** Serve para Dúvidas Gerais (Dentro do Servidor).\n\n'
        '- **"Solicitar Parceria"** Serve para você Pedir / Socilitar uma Parceria com sua Loja ou Outra coisa.\n\n'
        '- **"Solicitar Tag & Vips"** Serve para Você Pedir / Solicitar uma Tag dentro do Servidor do Discord ( como Vip, Plus, Lite e etc ).\n\n'
        '- **"Denunciar membro"** Serve para você Reportar um Jogador que Esteja Desrespeitando as Regras do Servidor.\n\n'
        '- **"Recrutamento"** Serve para Você ser Recrutado para ser Membro iniciante, Membro Oficial e etc...'
    )

    embed = discord.Embed(
        description=description,
        color=discord.Color.green(),
    )
    return embed


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        for ticket_id, ticket_data in TICKET_TYPES.items():
            self.add_item(TicketButton(ticket_id, ticket_data))


class TicketButton(discord.ui.Button):
    def __init__(self, ticket_id, ticket_data):
        super().__init__(
            label=ticket_data["label"],
            emoji=discord.PartialEmoji.from_str(ticket_data["emoji"]),
            style=ticket_data["style"],
            custom_id=f"ticket_panel:{ticket_id}",
        )
        self.ticket_id = ticket_id
        self.ticket_data = ticket_data

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketFormModal(self.ticket_id, self.ticket_data))


class TicketActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket",
        emoji=CLOSE_EMOJI,
        style=discord.ButtonStyle.red,
        custom_id="ticket_action:close",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Esse botão só funciona dentro de um ticket.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Não consegui conferir suas permissões.", ephemeral=True)
            return

        topic_data = parse_ticket_topic(interaction.channel.topic)
        owner_id = topic_data.get("ticket_owner")
        claimed_by = topic_data.get("ticket_claimed_by")

        can_close = (
            str(interaction.user.id) == owner_id
            or str(interaction.user.id) == claimed_by
            or user_has_any_role(interaction.user, ALL_TICKET_ROLE_IDS)
        )

        if not can_close:
            await interaction.response.send_message(
                "Você não pode fechar este ticket. Apenas quem abriu, quem reivindicou ou a equipe superior pode fechar.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Fechando ticket em 5 segundos...", ephemeral=True)
        await send_ticket_close_log(interaction, interaction.user)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user} ({interaction.user.id})")

    @discord.ui.button(
        label="Reivindicar Ticket",
        emoji=CLAIM_EMOJI,
        style=discord.ButtonStyle.gray,
        custom_id="ticket_action:claim",
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Esse botão só funciona dentro de um ticket.", ephemeral=True)
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Não consegui conferir suas permissões.", ephemeral=True)
            return

        topic_data = parse_ticket_topic(interaction.channel.topic)
        ticket_id = topic_data.get("ticket_type")
        owner_id = topic_data.get("ticket_owner")
        claimed_by = topic_data.get("ticket_claimed_by")
        opened_at = topic_data.get("ticket_opened_at")

        if not ticket_id or ticket_id not in TICKET_TYPES:
            await interaction.response.send_message("Não consegui identificar o tipo deste ticket.", ephemeral=True)
            return

        if str(interaction.user.id) == owner_id:
            await interaction.response.send_message("Quem abriu o ticket não pode reivindicar o próprio atendimento.", ephemeral=True)
            return

        if claimed_by:
            await interaction.response.send_message(f"Este ticket já foi reivindicado por <@{claimed_by}>.", ephemeral=True)
            return

        if not user_has_any_role(interaction.user, get_ticket_staff_role_ids(ticket_id)):
            await interaction.response.send_message("Você não tem permissão para atender este tipo de ticket.", ephemeral=True)
            return

        await interaction.channel.edit(
            topic=build_ticket_topic(owner_id, ticket_id, interaction.user.id, opened_at),
            reason=f"Ticket reivindicado por {interaction.user} ({interaction.user.id})",
        )

        embed = discord.Embed(
            title="Ticket Reivindicado",
            description=f"Este ticket foi reivindicado por {interaction.user.mention}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)


class TranscriptButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ver Transcrição",
        style=discord.ButtonStyle.gray,
        custom_id="ticket_action:transcript",
    )
    async def show_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        message = interaction.message
        if message is None:
            await interaction.response.send_message("Não consegui identificar o log desse ticket.", ephemeral=True)
            return

        transcript_path = TRANSCRIPT_DIR / f"{message.id}.txt"
        if not transcript_path.exists():
            await interaction.response.send_message("Não encontrei a transcrição desse ticket.", ephemeral=True)
            return

        transcript_file = discord.File(
            io.BytesIO(transcript_path.read_bytes()),
            filename=f"transcricao-{message.id}.txt",
        )
        await interaction.response.send_message(file=transcript_file, ephemeral=True)


class TicketFormModal(discord.ui.Modal):
    def __init__(self, ticket_id, ticket_data):
        super().__init__(title=ticket_data["label"])
        self.ticket_id = ticket_id
        self.ticket_data = ticket_data
        self.inputs: list[discord.ui.TextInput] = []

        for label, placeholder in TICKET_FORM_FIELDS[ticket_id]:
            text_input = discord.ui.TextInput(
                label=label,
                placeholder=placeholder,
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=1000,
            )
            self.inputs.append(text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        answers = [(item.label, item.value) for item in self.inputs]
        await create_ticket(interaction, self.ticket_id, self.ticket_data, answers)


async def create_ticket(interaction, ticket_id, ticket_data, answers):
    guild = interaction.guild
    user = interaction.user

    if guild is None or not isinstance(user, discord.Member):
        await interaction.response.send_message("Esse botão só funciona dentro do servidor.", ephemeral=True)
        return

    channel_name = clean_channel_name(f"{ticket_data['slug']}-{user.name}")
    existing = discord.utils.get(guild.text_channels, name=channel_name)

    if existing is not None:
        await interaction.response.send_message(
            f"Você já tem um ticket aberto: {existing.mention}",
            ephemeral=True,
        )
        return

    bot_member = guild.me
    if bot_member is None:
        await interaction.response.send_message("Não consegui conferir minhas permissões.", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
        ),
    }

    for role_id in get_ticket_staff_role_ids(ticket_id):
        role = guild.get_role(role_id)
        if role is None:
            continue

        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )

    category = guild.get_channel(config.TICKET_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message("Não encontrei a categoria configurada para criar tickets.", ephemeral=True)
        return

    opened_at = datetime.now()

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        topic=build_ticket_topic(user.id, ticket_id, opened_at.isoformat(timespec="seconds")),
        reason=f"Ticket aberto por {user} ({user.id})",
    )

    await ticket_channel.send(
        content=user.mention,
        embed=build_ticket_open_embed(user, ticket_id, ticket_data, answers, opened_at),
        view=TicketActionView(),
    )
    await send_ticket_open_log(interaction.client, ticket_channel, user, ticket_data, opened_at)
    await interaction.response.send_message(
        f"Ticket criado: {ticket_channel.mention}",
        ephemeral=True,
    )


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.panel_ready = False

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketActionView())
        self.bot.add_view(TranscriptButtonView())

        if self.panel_ready:
            return

        self.panel_ready = True
        await self.ensure_ticket_panel()

    async def ensure_ticket_panel(self):
        channel = self.bot.get_channel(config.TICKET_PANEL_CHANNEL_ID)
        if channel is None:
            channel = await self.bot.fetch_channel(config.TICKET_PANEL_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            print("Canal do painel de ticket nao e um canal de texto.")
            return

        panel_messages = []
        async for message in channel.history(limit=50):
            if message.author.id != self.bot.user.id:
                continue

            has_panel = any(
                embed.title == TICKET_PANEL_TITLE
                or (embed.description or "").startswith("#  <:ticket_3:1509547413558263848> __ CENTRA DE ATENDIMENTO__")
                for embed in message.embeds
            )
            if has_panel:
                panel_messages.append(message)

        embed = build_ticket_embed()
        view = TicketPanelView()

        if panel_messages:
            panel_messages.sort(key=lambda item: item.created_at)
            main_message = panel_messages[0]
            await main_message.edit(embed=embed, view=view)

            for duplicate in panel_messages[1:]:
                await duplicate.delete()
            return

        await channel.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
