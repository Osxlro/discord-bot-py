import discord
import logging
from services import lang_service

logger = logging.getLogger(__name__)

class Paginator(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], author_id: int, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author_id = author_id
        self.current_page = 0
        
        # Configuramos el estado inicial de los botones
        self.update_buttons()

    def update_buttons(self):
        # Desactivar botones de retroceso si estamos en la primera página
        self.first_page.disabled = (self.current_page == 0)
        self.prev_page.disabled = (self.current_page == 0)
        
        # Desactivar botones de avance si estamos en la última página
        self.next_page.disabled = (self.current_page == len(self.pages) - 1)
        self.last_page.disabled = (self.current_page == len(self.pages) - 1)
        
        # Actualizar contador
        self.counter.label = f"{self.current_page + 1}/{len(self.pages)}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Solo quien ejecutó el comando puede cambiar de página
        if interaction.user.id != self.author_id:
            logger.debug(f"Intento de paginación no autorizado: {interaction.user} en menú de {self.author_id}")
            lang = await lang_service.get_guild_lang(interaction.guild_id)
            await interaction.response.send_message(lang_service.get_text("dev_interaction_error", lang), ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        # Desactivar todo cuando se acabe el tiempo
        for child in self.children:
            child.disabled = True
        # Nota: Para editar el mensaje original se necesitaría guardar la referencia del mensaje
        # pero en interacciones híbridas a veces es complejo. Por ahora solo deja de responder.

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.gray, disabled=True)
    async def counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass # Botón meramente visual

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.pages) - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)