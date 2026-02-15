import discord
from services import db_service, lang_service
from config import settings

class ProfileView(discord.ui.View):
    def __init__(self, bot, member, lang, user_data, guild_data):
        super().__init__(timeout=120)
        self.bot = bot
        self.member = member
        self.lang = lang
        self.user_data = user_data
        self.guild_data = guild_data
        
        # Configurar etiquetas de botones
        self.btn_general.label = lang_service.get_text("profile_btn_general", lang)
        self.btn_stats.label = lang_service.get_text("profile_btn_stats", lang)
        self.btn_msgs.label = lang_service.get_text("profile_btn_msgs", lang)

    def _get_base_embed(self):
        embed = discord.Embed(color=settings.COLORS["INFO"])
        embed.set_author(name=lang_service.get_text("profile_title", self.lang, user=self.member.display_name), icon_url=self.member.display_avatar.url)
        embed.set_thumbnail(url=self.member.display_avatar.url)
        
        joined_date = self.member.joined_at.strftime("%d/%m/%Y") if self.member.joined_at else "??/??/????"
        footer_text = lang_service.get_text("profile_joined", self.lang, date=joined_date)
        embed.set_footer(text=footer_text)
        return embed

    def get_general_embed(self):
        embed = self._get_base_embed()
        desc = self.user_data.get("description") or lang_service.get_text("profile_desc", self.lang)
        bday = self.user_data.get("birthday") or lang_service.get_text("profile_no_bday", self.lang)
        prefix = self.user_data.get("custom_prefix") or settings.CONFIG["bot_config"]["prefix"]
        
        embed.add_field(name=lang_service.get_text("profile_field_desc", self.lang), value=f"```\n{desc}\n```", inline=False)
        embed.add_field(name=lang_service.get_text("profile_field_bday", self.lang), value=f"🎂 {bday}", inline=True)
        embed.add_field(name=lang_service.get_text("profile_field_prefix", self.lang), value=f"⌨️ `{prefix}`", inline=True)
        embed.add_field(name=lang_service.get_text("profile_field_coins", self.lang), value="🪙 `0` *(Próximamente)*", inline=True)
        return embed

    def get_stats_embed(self):
        embed = self._get_base_embed()
        embed.color = settings.COLORS["XP"]
        embed.title = lang_service.get_text("profile_server_stats", self.lang)
        
        lvl = self.guild_data.get("level", 1)
        xp = self.guild_data.get("xp", 0)
        rebirths = self.guild_data.get("rebirths", 0)
        next_xp = db_service.calculate_xp_required(lvl)
        
        # Barra de progreso (Reusando lógica de niveles)
        filled = settings.UI_CONFIG["PROGRESS_BAR_FILLED"]
        empty = settings.UI_CONFIG["PROGRESS_BAR_EMPTY"]
        bar_len = settings.UI_CONFIG["PROFILE_BAR_LENGTH"]
        progress = int((xp / next_xp) * bar_len)
        bar = (filled * progress) + (empty * (bar_len - progress))
        
        stats_text = (
            f"🏆 **{lang_service.get_text('profile_field_lvl', self.lang)}:** `{lvl}`\n"
            f"🌀 **{lang_service.get_text('profile_field_rebirths', self.lang)}:** `{rebirths}`\n"
            f"✨ **{lang_service.get_text('profile_field_xp', self.lang)}:** `{xp}/{next_xp}`\n"
            f"`{bar}`"
        )
        embed.description = stats_text
        return embed

    def get_msgs_embed(self):
        embed = self._get_base_embed()
        embed.title = lang_service.get_text("profile_custom_msgs", self.lang)
        
        lvl_msg = self.user_data.get("personal_level_msg") or "Default"
        bday_msg = self.user_data.get("personal_birthday_msg") or "Default"
        
        embed.add_field(name="🆙 Level Up Msg", value=f"```\n{lvl_msg}\n```", inline=False)
        embed.add_field(name="🎂 Birthday Msg", value=f"```\n{bday_msg}\n```", inline=False)
        return embed

    async def _update(self, interaction, embed, style_idx):
        tabs = [self.btn_general, self.btn_stats, self.btn_msgs]
        for i, child in enumerate(tabs):
            child.style = discord.ButtonStyle.primary if i == style_idx else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary, row=0)
    async def btn_general(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, self.get_general_embed(), 0)

    @discord.ui.button(style=discord.ButtonStyle.secondary, row=0)
    async def btn_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, self.get_stats_embed(), 1)

    @discord.ui.button(style=discord.ButtonStyle.secondary, row=0)
    async def btn_msgs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, self.get_msgs_embed(), 2)

async def get_profile_view(bot, member, lang):
    """Genera la vista y el embed inicial del perfil."""
    # Obtener datos de la DB
    user_data = await db_service.fetch_one("SELECT * FROM users WHERE user_id = ?", (member.id,))
    guild_data = await db_service.fetch_one("SELECT * FROM guild_stats WHERE guild_id = ? AND user_id = ?", (member.guild.id, member.id))
    
    # Normalizar si no existen
    if not user_data:
        user_data = {"description": None, "birthday": None, "custom_prefix": None}
    if not guild_data:
        guild_data = {"level": 1, "xp": 0, "rebirths": 0}
    else:
        guild_data = dict(guild_data)
        
    user_data = dict(user_data)
    
    view = ProfileView(bot, member, lang, user_data, guild_data)
    return view, view.get_general_embed()
