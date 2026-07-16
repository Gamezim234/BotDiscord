from __future__ import annotations

import io
from datetime import datetime

import discord
from discord.ext import commands

from config import DEV_USER_ID, IDEA_CHANNEL_ID


QUESTION_STEPS = [
    [
        {
            "label": "Qual e a ideia principal?",
            "title": "1. Explicação breve da ideia",
            "placeholder": "Seja especifico: o que o bot vai fazer, para quem e em qual situacao?",
        },
        {
            "label": "O que a ideia resolve?",
            "title": "2. Objetivo principal",
            "placeholder": "Explique o problema atual e como o bot vai resolver isso.",
        },
        {
            "label": "Quem vai usar?",
            "title": "3. Quem vai usar",
            "placeholder": "Liste os cargos/usuarios e em que momento cada um participa.",
        },
        {
            "label": "Como vai ser acessado?",
            "title": "4. Comandos ou formas de acesso",
            "placeholder": "Diga comando/botao/menu exato e o que acontece ao usar.",
        },
    ],
    [
        {
            "label": "Onde vai funcionar?",
            "title": "5. Canais ou chats específicos",
            "placeholder": "Diga canal, categoria, DM ou onde o bot deve criar/mandar mensagens.",
        },
        {
            "label": "O que o usuario envia?",
            "title": "6. Informações que o usuário precisa enviar",
            "placeholder": "Liste cada campo que o usuario preenche e quais sao obrigatorios.",
        },
        {
            "label": "O que o admin envia?",
            "title": "7. Informações que o administrador precisa enviar",
            "placeholder": "Explique o que o admin avalia, responde, aprova ou registra.",
        },
        {
            "label": "Quais funcoes precisa ter?",
            "title": "8. Funções que precisa ter",
            "placeholder": "Liste as acoes do bot em detalhes, uma por uma, sem palavras soltas.",
        },
    ],
    [
        {
            "label": "Quem pode usar cada coisa?",
            "title": "9. Permissões",
            "placeholder": "Diga cargo por cargo o que pode ver, usar, aprovar ou configurar.",
        },
        {
            "label": "Qual o passo a passo?",
            "title": "10. Fluxo de funcionamento",
            "placeholder": "Explique o fluxo completo, do primeiro clique ate finalizar.",
        },
        {
            "label": "O que o admin configura?",
            "title": "11. Configurações necessárias",
            "placeholder": "Liste configuracoes editaveis: canais, cargos, notas, mensagens, etc.",
        },
        {
            "label": "Tem observacoes finais?",
            "title": "12. Observações finais",
            "placeholder": "Adicione regras, excecoes, aparencia desejada ou detalhes importantes.",
        },
    ],
]

FORM_TITLES = [
    "Ideia do bot - Parte 1/3",
    "Ideia do bot - Parte 2/3",
    "Ideia do bot - Parte 3/3",
]

pending_forms = {}


def build_report(user, answers):
    display_name = getattr(user, "display_name", user.name)
    lines = [
        "NOVA IDEIA ENVIADA",
        "",
        f"Usuario: {display_name}",
        f"Username: {user}",
        f"ID: {user.id}",
        f"Mencao: <@{user.id}>",
        f"Enviada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "",
    ]

    for step in QUESTION_STEPS:
        for question in step:
            lines.append(question["title"])
            lines.append(answers.get(question["title"], "Nao informado."))
            lines.append("")

    return "\n".join(lines)


def build_step_embed(step_index):
    return discord.Embed(
        title=f"Formulario de ideia - Parte {step_index + 1}/3",
        description="Responda com detalhes. Evite respostas de uma palavra; explique exatamente como a ideia deve funcionar.",
        color=discord.Color.blurple(),
    )


def get_step_button_label(step_index):
    if step_index == 0:
        return "Iniciar formulario"
    return "Continuar formulario"


async def send_report_to_dev(bot, user, report):
    dev = await bot.fetch_user(DEV_USER_ID)
    display_name = getattr(user, "display_name", user.name)
    header = f"Nova ideia recebida de {display_name} ({user} | {user.id}):"

    if len(report) <= 1900:
        await dev.send(header)
        await dev.send(f"```text\n{report}\n```")
        return

    report_file = discord.File(io.BytesIO(report.encode("utf-8")), filename="ideia_bot.txt")
    await dev.send(header, file=report_file)


class ContinueButton(discord.ui.View):
    def __init__(self, bot, step_index):
        super().__init__(timeout=300)
        self.bot = bot
        self.step_index = step_index
        self.open_form.label = get_step_button_label(step_index)

    @discord.ui.button(label="Continuar formulario", style=discord.ButtonStyle.primary)
    async def open_form(self, interaction, button):
        await interaction.response.send_modal(IdeaModal(self.bot, self.step_index))


class StartIdeaButton(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.open_form.label = get_step_button_label(0)

    @discord.ui.button(label="Iniciar formulario", style=discord.ButtonStyle.primary)
    async def open_form(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Esse formulario foi aberto para outra pessoa. Use `!ideia` para abrir o seu.",
                ephemeral=True,
            )
            return

        pending_forms[interaction.user.id] = {}
        await interaction.response.send_modal(IdeaModal(self.bot, 0))


class IdeaModal(discord.ui.Modal):
    def __init__(self, bot, step_index):
        super().__init__(title=FORM_TITLES[step_index])
        self.bot = bot
        self.step_index = step_index
        self.inputs: list[discord.ui.TextInput] = []
        self.question_titles = []

        for question in QUESTION_STEPS[step_index]:
            text_input = discord.ui.TextInput(
                label=question["label"],
                placeholder=question["placeholder"],
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=1000,
            )
            self.question_titles.append(question["title"])
            self.inputs.append(text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction):
        user_answers = pending_forms.setdefault(interaction.user.id, {})

        for title, item in zip(self.question_titles, self.inputs):
            user_answers[title] = item.value

        next_step = self.step_index + 1
        if next_step < len(QUESTION_STEPS):
            await interaction.response.send_message(
                embed=build_step_embed(next_step),
                view=ContinueButton(self.bot, next_step),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        report = build_report(interaction.user, user_answers)
        await send_report_to_dev(self.bot, interaction.user, report)
        pending_forms.pop(interaction.user.id, None)

        embed = discord.Embed(
            title="Ideia enviada",
            description="Pronto. Sua ideia foi enviada no privado do desenvolvedor.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class IdeaForm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ideia", description="Enviar uma ideia para o desenvolvedor.")
    async def ideia(self, ctx: commands.Context):
        if ctx.channel is None or ctx.channel.id != IDEA_CHANNEL_ID:
            await ctx.reply(
                f"Use este comando apenas no canal <#{IDEA_CHANNEL_ID}>.",
                ephemeral=ctx.interaction is not None,
            )
            return

        pending_forms[ctx.author.id] = {}
        await ctx.reply(
            embed=build_step_embed(0),
            view=StartIdeaButton(self.bot, ctx.author.id),
            ephemeral=ctx.interaction is not None,
        )


async def setup(bot):
    await bot.add_cog(IdeaForm(bot))
