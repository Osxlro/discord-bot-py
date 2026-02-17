import discord
from config import settings
from services.core import lang_service
from services.utils import embed_service

def get_general_embed(target: discord.Member, user_data: dict, lang: str) -> discord.Embed:
    """Genera el embed de información general (global)."""
    desc = user_data['description'] if user_data else lang_service.get_text("profile_desc", lang)
    cumple = user_data['birthday'] if user_data and user_data['birthday'] else lang_service.get_text("profile_no_bday", lang)
    prefix = user_data['custom_prefix'] if user_data and user_data['custom_prefix'] else settings.CONFIG["bot_config"]["prefix"]
    
    title = lang_service.get_text("profile_title", lang, user=target.display_name)
    embed = discord.Embed(title=title, color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    
    embed.add_field(name=lang_service.get_text("profile_field_desc", lang), value=f"*{desc}*", inline=False)
    embed.add_field(name=lang_service.get_text("profile_field_bday", lang), value=f"{cumple}", inline=True)
    embed.add_field(name=lang_service.get_text("profile_field_prefix", lang), value=f"`{prefix}`", inline=True)
    embed.add_field(name=lang_service.get_text("profile_field_coins", lang), value="`0` (Soon)", inline=True)

    return embed

def get_stats_embed(target: discord.Member, guild_data: dict, xp_next: int, lang: str) -> discord.Embed:
    """Genera el embed de estadísticas del servidor."""
    xp = guild_data['xp'] if guild_data else 0
    nivel = guild_data['level'] if guild_data else 1
    rebirths = guild_data['rebirths'] if guild_data else 0
    
    progreso = min(xp / xp_next, 1.0) if xp_next > 0 else 1.0
    bar_len = settings.UI_CONFIG["PROFILE_BAR_LENGTH"]
    bloques = int(progreso * bar_len)
    barra = settings.UI_CONFIG["PROGRESS_BAR_FILLED"] * bloques + settings.UI_CONFIG["PROGRESS_BAR_EMPTY"] * (bar_len - bloques)

    title = lang_service.get_text("profile_server_stats", lang).replace("-", "").strip()
    embed = discord.Embed(title=f"{title} - {target.display_name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)

    embed.add_field(name=lang_service.get_text("profile_field_lvl", lang), value=f"**{nivel}**", inline=True)
    embed.add_field(name=lang_service.get_text("profile_field_rebirths", lang), value=f"**{rebirths}**", inline=True)
    embed.add_field(name=lang_service.get_text("profile_field_xp", lang), value=f"{xp}", inline=True)
    
    progress_label = lang_service.get_text("profile_progress", lang, percent=int(progreso*100))
    embed.add_field(name=progress_label, value=f"`{barra}` {xp}/{xp_next}", inline=False)
    
    return embed

def get_messages_embed(target: discord.Member, user_data: dict, lang: str) -> discord.Embed:
    """Genera el embed de previsualización de mensajes personalizados."""
    title = lang_service.get_text("profile_custom_msgs", lang).replace("-", "").strip()
    embed = discord.Embed(title=f"{title} - {target.display_name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)

    msgs = ""
    if user_data:
        limit = settings.UI_CONFIG["MSG_PREVIEW_TRUNCATE"]
        if user_data['personal_level_msg']: 
            msgs += lang_service.get_text("profile_preview_lvl", lang, msg=user_data['personal_level_msg'][:limit]) + "\n"
        if user_data['personal_birthday_msg']: 
            msgs += lang_service.get_text("profile_preview_bday", lang, msg=user_data['personal_birthday_msg'][:limit]) + "\n"
    
    embed.description = msgs if msgs else lang_service.get_text("log_none", lang)
    return embed

class ProfileView(discord.ui.View):
    """Vista con botones para navegar por las secciones del perfil."""
    def __init__(self, target, user_data, guild_data, xp_next, lang, author_id):
        super().__init__(timeout=settings.TIMEOUT_CONFIG.get("BOT_INFO", 120))
        self.target, self.user_data, self.guild_data = target, user_data, guild_data
        self.xp_next, self.lang, self.author_id = xp_next, lang, author_id
        self.message = None
        
        self.btn_general.label = lang_service.get_text("profile_btn_general", lang)
        self.btn_stats.label = lang_service.get_text("profile_btn_stats", lang)
        self.btn_msgs.label = lang_service.get_text("profile_btn_msgs", lang)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(lang_service.get_text("dev_interaction_error", self.lang), ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children: child.disabled = True
        try: await self.message.edit(view=self)
        except: pass

    async def _update(self, interaction, embed, style_idx):
        tabs = [self.btn_general, self.btn_stats, self.btn_msgs]
        for i, child in enumerate(tabs):
            child.style = discord.ButtonStyle.primary if i == style_idx else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def btn_general(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, get_general_embed(self.target, self.user_data, self.lang), 0)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, get_stats_embed(self.target, self.guild_data, self.xp_next, self.lang), 1)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_msgs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, get_messages_embed(self.target, self.user_data, self.lang), 2)

def get_profile_embed(target: discord.Member, user_data: dict, guild_data: dict, xp_next: int, lang: str) -> discord.Embed:
    """Mantiene compatibilidad con el wrapper de servicio (retorna la vista general)."""
    return get_general_embed(target, user_data, lang)

def get_profile_update_success_embed(lang: str, type_key: str) -> discord.Embed:
    """Genera un embed de éxito para actualizaciones de perfil."""
    title = lang_service.get_text("profile_update_success", lang)
    desc = lang_service.get_text(type_key, lang)
    return embed_service.success(title, desc, lite=True)