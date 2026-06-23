import discord
from services.core import lang_service
from services.utils import embed_service

HANGMAN_PICS = [
    # 6 vidas restantes (0 fallos)
    "```\n"
    "  +---+\n"
    "  |   |\n"
    "      |\n"
    "      |\n"
    "      |\n"
    "      |\n"
    "=========\n"
    "```",
    # 5 vidas restantes (1 fallo)
    "```\n"
    "  +---+\n"
    "  |   |\n"
    "  O   |\n"
    "      |\n"
    "      |\n"
    "      |\n"
    "=========\n"
    "```",
    # 4 vidas restantes (2 fallos)
    "```\n"
    "  +---+\n"
    "  |   |\n"
    "  O   |\n"
    "  |   |\n"
    "      |\n"
    "      |\n"
    "=========\n"
    "```",
    # 3 vidas restantes (3 fallos)
    "```\n"
    "  +---+\n"
    "  |   |\n"
    "  O   |\n"
    " /|   |\n"
    "      |\n"
    "      |\n"
    "=========\n"
    "```",
    # 2 vidas restantes (4 fallos)
    "```\n"
    "  +---+\n"
    "  |   |\n"
    "  O   |\n"
    " /|\\  |\n"
    "      |\n"
    "      |\n"
    "=========\n"
    "```",
    # 1 vida restante (5 fallos)
    "```\n"
    "  +---+\n"
    "  |   |\n"
    "  O   |\n"
    " /|\\  |\n"
    " /    |\n"
    "      |\n"
    "=========\n"
    "```",
    # 0 vidas restantes (6 fallos)
    "```\n"
    "  +---+\n"
    "  |   |\n"
    "  O   |\n"
    " /|\\  |\n"
    " / \\  |\n"
    "      |\n"
    "=========\n"
    "```"
]

class ModeSelect(discord.ui.Select):
    def __init__(self, lang: str):
        options = [
            discord.SelectOption(
                label=lang_service.get_text("hangman_mode_solo", lang),
                value="solo",
                description=lang_service.get_text("hangman_mode_solo_desc", lang),
                default=True
            ),
            discord.SelectOption(
                label=lang_service.get_text("hangman_mode_multi", lang),
                value="multiplayer",
                description=lang_service.get_text("hangman_mode_multi_desc", lang)
            )
        ]
        super().__init__(
            placeholder=lang_service.get_text("hangman_mode_placeholder", lang),
            options=options,
            custom_id="hangman_mode_select",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.mode = self.values[0]
        for opt in self.options:
            opt.default = (opt.value == self.view.mode)
        await self.view.update_embed(interaction)

class DifficultySelect(discord.ui.Select):
    def __init__(self, lang: str):
        options = [
            discord.SelectOption(label=lang_service.get_text("hangman_diff_easy", lang), value="fácil", description="3-5 letras"),
            discord.SelectOption(label=lang_service.get_text("hangman_diff_medium", lang), value="medio", description="6-8 letras"),
            discord.SelectOption(label=lang_service.get_text("hangman_diff_hard", lang), value="difícil", description="9+ letras"),
            discord.SelectOption(label=lang_service.get_text("hangman_diff_any", lang), value="cualquiera", description="Cualquier longitud", default=True)
        ]
        super().__init__(
            placeholder=lang_service.get_text("hangman_diff_placeholder", lang),
            options=options,
            custom_id="hangman_diff_select",
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.difficulty = self.values[0]
        for opt in self.options:
            opt.default = (opt.value == self.view.difficulty)
        await self.view.update_embed(interaction)

class CategorySelect(discord.ui.Select):
    def __init__(self, lang: str):
        options = [
            discord.SelectOption(label=lang_service.get_text("hangman_cat_any", lang), value="cualquiera", default=True),
            discord.SelectOption(label=lang_service.get_text("hangman_cat_animal", lang), value="animal"),
            discord.SelectOption(label=lang_service.get_text("hangman_cat_country", lang), value="country"),
            discord.SelectOption(label=lang_service.get_text("hangman_cat_food", lang), value="food"),
            discord.SelectOption(label=lang_service.get_text("hangman_cat_plant", lang), value="plant"),
            discord.SelectOption(label=lang_service.get_text("hangman_cat_sport", lang), value="sport")
        ]
        super().__init__(
            placeholder=lang_service.get_text("hangman_cat_placeholder", lang),
            options=options,
            custom_id="hangman_cat_select",
            row=2
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.category = self.values[0]
        for opt in self.options:
            opt.default = (opt.value == self.view.category)
        await self.view.update_embed(interaction)

class HangmanConfigView(discord.ui.View):
    def __init__(self, author: discord.Member, lang: str):
        super().__init__(timeout=60.0)
        self.author = author
        self.lang = lang
        self.message = None
        
        self.mode = "solo"
        self.difficulty = "cualquiera"
        self.category = "cualquiera"
        self.status = None  # 'start' o 'cancel'
        
        self.add_item(ModeSelect(lang))
        self.add_item(DifficultySelect(lang))
        self.add_item(CategorySelect(lang))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            msg = lang_service.get_text("trivia_not_yours", self.lang)
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    def get_embed(self) -> discord.Embed:
        title = lang_service.get_text("hangman_config_title", self.lang)
        
        diff_key_map = {
            "fácil": "hangman_diff_easy",
            "medio": "hangman_diff_medium",
            "difícil": "hangman_diff_hard",
            "cualquiera": "hangman_diff_any"
        }
        cat_key_map = {
            "cualquiera": "hangman_cat_any",
            "animal": "hangman_cat_animal",
            "country": "hangman_cat_country",
            "food": "hangman_cat_food",
            "plant": "hangman_cat_plant",
            "sport": "hangman_cat_sport"
        }
        
        # Traducir los valores para mostrarlos bonito en el embed
        mode_display = lang_service.get_text(f"hangman_mode_{self.mode[:5]}", self.lang)
        diff_display = lang_service.get_text(diff_key_map.get(self.difficulty, "hangman_diff_any"), self.lang)
        cat_display = lang_service.get_text(cat_key_map.get(self.category, "hangman_cat_any"), self.lang)
        
        desc = (
            f"> **{lang_service.get_text('hangman_config_mode', self.lang)}:** {mode_display}\n"
            f"> **{lang_service.get_text('hangman_config_diff', self.lang)}:** {diff_display}\n"
            f"> **{lang_service.get_text('hangman_config_cat', self.lang)}:** {cat_display}\n\n"
            f"{lang_service.get_text('hangman_config_instructions', self.lang)}"
        )
        return embed_service.fun(title, desc)

    async def update_embed(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Iniciar", style=discord.ButtonStyle.success, custom_id="hangman_start_btn", row=3)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.status = "start"
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, custom_id="hangman_cancel_btn", row=3)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.status = "cancel"
        self.stop()
        await interaction.response.edit_message(
            embed=embed_service.info(
                lang_service.get_text("hangman_cancelled_title", self.lang),
                lang_service.get_text("hangman_cancelled_desc", self.lang)
            ),
            view=None
        )

    async def on_timeout(self):
        self.stop()
        if self.message:
            try:
                await self.message.edit(
                    embed=embed_service.warning(
                        lang_service.get_text("hangman_timeout_title", self.lang),
                        lang_service.get_text("hangman_timeout_desc", self.lang)
                    ),
                    view=None
                )
            except Exception:
                pass

class HangmanGameView(discord.ui.View):
    def __init__(self, author: discord.Member, lang: str, is_solo: bool = True):
        # Timeout largo para la partida (5 minutos)
        super().__init__(timeout=300.0)
        self.author = author
        self.lang = lang
        self.surrendered = False
        self.is_solo = is_solo
        self.active_task = None
        
        if not is_solo:
            # En multijugador no se permite rendirse individualmente por botón
            self.clear_items()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.is_solo and interaction.user.id != self.author.id:
            msg = lang_service.get_text("trivia_not_yours", self.lang)
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Rendirse", style=discord.ButtonStyle.danger, custom_id="hangman_surrender_btn")
    async def surrender(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.surrendered = True
        self.stop()
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()

    async def on_timeout(self):
        self.stop()
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
