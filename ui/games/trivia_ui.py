import discord
import random
import logging
from config import settings
from services.core import db_service, lang_service
from services.utils import embed_service

logger = logging.getLogger(__name__)

class TriviaView(discord.ui.View):
    def __init__(self, author: discord.Member, correct_index: int, options: list[str], correct_answer: str, difficulty: str, lang: str):
        super().__init__(timeout=30.0)
        self.author = author
        self.correct_index = correct_index
        self.options = options
        self.correct_answer = correct_answer
        self.difficulty = difficulty
        self.lang = lang
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            msg = lang_service.get_text("trivia_not_yours", self.lang)
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    def disable_all_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def process_answer(self, interaction: discord.Interaction, selected_index: int):
        self.disable_all_buttons()
        self.stop()

        if selected_index == self.correct_index:
            # Recompensa configurada por dificultad
            rewards = settings.TRIVIA_CONFIG["REWARDS"].get(self.difficulty, (10, 20))
            coins = random.randint(rewards[0], rewards[1])
            await db_service.add_user_coins(interaction.user.id, coins)
            
            title = lang_service.get_text("trivia_correct_title", self.lang)
            desc = lang_service.get_text("trivia_correct_desc", self.lang, answer=self.correct_answer, coins=coins)
            embed = embed_service.success(title, desc)
        else:
            title = lang_service.get_text("trivia_incorrect_title", self.lang)
            desc = lang_service.get_text("trivia_incorrect_desc", self.lang, correct=self.correct_answer)
            embed = embed_service.error(title, desc)

        # Eliminar los botones al ganar o perder
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="A", style=discord.ButtonStyle.primary, custom_id="trivia_btn_a")
    async def button_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, 0)

    @discord.ui.button(label="B", style=discord.ButtonStyle.primary, custom_id="trivia_btn_b")
    async def button_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, 1)

    @discord.ui.button(label="C", style=discord.ButtonStyle.primary, custom_id="trivia_btn_c")
    async def button_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, 2)

    @discord.ui.button(label="D", style=discord.ButtonStyle.primary, custom_id="trivia_btn_d")
    async def button_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, 3)

    async def on_timeout(self):
        """Eliminar los botones al agotarse el tiempo."""
        if self.message:
            self.disable_all_buttons()
            try:
                title = lang_service.get_text("trivia_timeout_title", self.lang)
                desc = lang_service.get_text("trivia_timeout_desc", self.lang, correct=self.correct_answer)
                embed = embed_service.warning(title, desc)
                # Pasar view=None para eliminar los botones
                await self.message.edit(embed=embed, view=None)
            except Exception as e:
                logger.warning(f"Error al editar mensaje de trivia en timeout: {e}")
