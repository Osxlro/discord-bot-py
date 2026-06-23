import discord
from config import settings
from services.utils import embed_service
from services.core import lang_service

def get_ping_embed(ms: int, lang: str) -> discord.Embed:
    txt = lang_service.get_text("ping_msg", lang, ms=ms)
    return embed_service.info(lang_service.get_text("title_ping", lang), txt, lite=True)

def get_calc_success_embed(num1: float, op_symbol: str, num2: float, res: float, lang: str) -> discord.Embed:
    txt = lang_service.get_text("calc_result", lang, a=num1, op=op_symbol, b=num2, res=res)
    return embed_service.success(lang_service.get_text("title_math", lang), txt)

def get_serverinfo_embed(guild: discord.Guild, config: dict, stats: dict, lang: str) -> discord.Embed:
    title = lang_service.get_text("serverinfo_title", lang, name=guild.name)
    
    # Usar el color del bot en el servidor o el azul Discord de marca (0x5865F2)
    color = guild.me.color if guild.me.color.value != 0 else discord.Color(0x5865F2)
    embed = discord.Embed(title=title, color=color)
    
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    if guild.banner: embed.set_image(url=guild.banner.url)

    # Fila 1: Información Básica
    embed.add_field(name=lang_service.get_text("serverinfo_owner", lang), value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_id", lang), value=f"`{guild.id}`", inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_created", lang), value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)

    # Fila 2: Información del Servidor (Boosts, Emojis, Verificación)
    verification_map = {
        "none": {"es": "Ninguno", "en": "None", "pt": "Nenhum", "fr": "Aucun"},
        "low": {"es": "Bajo", "en": "Low", "pt": "Baixo", "fr": "Faible"},
        "medium": {"es": "Medio", "en": "Medium", "pt": "Médio", "fr": "Moyen"},
        "high": {"es": "Alto", "en": "High", "pt": "Alto", "fr": "Élevé"},
        "highest": {"es": "Extremo", "en": "Extreme", "pt": "Extremo", "fr": "Maximum"}
    }
    raw_ver = stats.get('verification', 'none')
    ver_txt = verification_map.get(raw_ver, verification_map["none"]).get(lang, "None")
    
    emojis_txt = f"😊 {stats['emojis']} / 👾 {stats['stickers']}"
    boost_tier_txt = f"Tier {stats['tier']} ({stats['boosts']} 🚀)"

    embed.add_field(name=lang_service.get_text("serverinfo_boost_tier", lang), value=boost_tier_txt, inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_emojis", lang), value=emojis_txt, inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_verification", lang), value=ver_txt, inline=True)

    # Fila 3: Estadísticas del Servidor
    stats_txt = lang_service.get_text("serverinfo_stats_desc", lang,
        total=guild.member_count, humans=stats['humans'], bots=stats['bots'],
        roles=stats['roles'], boosts=stats['boosts'],
        channels=stats['channels'], cats=stats['cats'],
        text=stats['text'], voice=stats['voice']
    )
    formatted_stats = "\n".join(f"> {line}" for line in stats_txt.split('\n'))
    embed.add_field(name=lang_service.get_text("serverinfo_stats", lang), value=formatted_stats, inline=False)

    # Fila 4: Configuración del Bot
    def fmt(val, type_):
        if not val: return lang_service.get_text("serverinfo_not_set", lang)
        return f"<#{val}>" if type_ == "ch" else f"<@&{val}>"

    lang_key = f"lang_name_{config.get('language', 'es')}"
    lang_name = lang_service.get_text(lang_key, lang)
    
    conf_txt = lang_service.get_text("serverinfo_conf_desc", lang,
        language=lang_name,
        welcome=fmt(config.get("welcome_channel_id"), "ch"),
        confess=fmt(config.get("confessions_channel_id"), "ch"),
        logs=fmt(config.get("logs_channel_id"), "ch"),
        bday=fmt(config.get("birthday_channel_id"), "ch"),
        autorole=fmt(config.get("autorole_id"), "role"),
        wordday_ch=fmt(config.get("wordday_channel_id"), "ch"),
        wordday_role=fmt(config.get("wordday_role_id"), "role")
    )
    formatted_conf = "\n".join(f"> {line}" for line in conf_txt.split('\n'))
    embed.add_field(name=lang_service.get_text("serverinfo_config", lang), value=formatted_conf, inline=False)

    return embed

def get_serverinfo_general_embed(guild: discord.Guild, stats: dict, lang: str) -> discord.Embed:
    title = lang_service.get_text("serverinfo_title", lang, name=guild.name)
    color = guild.me.color if guild.me.color.value != 0 else discord.Color(0x5865F2)
    embed = discord.Embed(title=title, color=color)
    
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    if guild.banner: embed.set_image(url=guild.banner.url)

    embed.add_field(name=lang_service.get_text("serverinfo_owner", lang), value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_id", lang), value=f"`{guild.id}`", inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_created", lang), value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)

    verification_map = {
        "none": {"es": "Ninguno", "en": "None", "pt": "Nenhum", "fr": "Aucun"},
        "low": {"es": "Bajo", "en": "Low", "pt": "Baixo", "fr": "Faible"},
        "medium": {"es": "Medio", "en": "Medium", "pt": "Médio", "fr": "Moyen"},
        "high": {"es": "Alto", "en": "High", "pt": "Alto", "fr": "Élevé"},
        "highest": {"es": "Extremo", "en": "Extreme", "pt": "Extremo", "fr": "Maximum"}
    }
    raw_ver = stats.get('verification', 'none')
    ver_txt = verification_map.get(raw_ver, verification_map["none"]).get(lang, "None")
    
    emojis_txt = f"😊 {stats['emojis']} / 👾 {stats['stickers']}"
    boost_tier_txt = f"Tier {stats['tier']} ({stats['boosts']} 🚀)"

    embed.add_field(name=lang_service.get_text("serverinfo_boost_tier", lang), value=boost_tier_txt, inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_emojis", lang), value=emojis_txt, inline=True)
    embed.add_field(name=lang_service.get_text("serverinfo_verification", lang), value=ver_txt, inline=True)

    return embed

def get_serverinfo_stats_embed(guild: discord.Guild, stats: dict, lang: str) -> discord.Embed:
    title = f"{lang_service.get_text('serverinfo_stats', lang)} - {guild.name}"
    color = guild.me.color if guild.me.color.value != 0 else discord.Color(0x5865F2)
    embed = discord.Embed(title=title, color=color)
    
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)

    stats_txt = lang_service.get_text("serverinfo_stats_desc", lang,
        total=guild.member_count, humans=stats['humans'], bots=stats['bots'],
        roles=stats['roles'], boosts=stats['boosts'],
        channels=stats['channels'], cats=stats['cats'],
        text=stats['text'], voice=stats['voice']
    )
    formatted_stats = "\n".join(f"> {line}" for line in stats_txt.split('\n'))
    embed.add_field(name=lang_service.get_text("serverinfo_stats", lang), value=formatted_stats, inline=False)

    return embed

def get_serverinfo_config_embed(guild: discord.Guild, config: dict, stream_alerts: list, lang: str) -> discord.Embed:
    title = f"{lang_service.get_text('serverinfo_config', lang)} - {guild.name}"
    color = guild.me.color if guild.me.color.value != 0 else discord.Color(0x5865F2)
    embed = discord.Embed(title=title, color=color)
    
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)

    # Helpers de formateo
    def fmt_ch(val):
        return f"<#{val}>" if val and val != 0 else lang_service.get_text("setup_disabled", lang)

    def fmt_role(val):
        return f"<@&{val}>" if val and val != 0 else lang_service.get_text("setup_disabled", lang)

    # Obtener nombre del idioma configurado
    lang_key = f"lang_name_{config.get('language', 'es')}"
    lang_name = lang_service.get_text(lang_key, lang)

    # Estado de Chaos
    chaos_enabled = bool(config.get("chaos_enabled", 1))
    chaos_prob = config.get("chaos_probability", 0.01) * 100
    chaos_status = f"✅ ({chaos_prob:.1f}%)" if chaos_enabled else lang_service.get_text("setup_disabled", lang)

    # Estado de Días Festivos
    festive_enabled = bool(config.get("festivedays_enabled", 0))
    festive_ch = config.get("festivedays_channel_id", 0)
    festive_role = config.get("festivedays_role_id", 0)
    if festive_enabled:
        festive_status = f"✅ en <#{festive_ch}>"
        if festive_role:
            festive_status += f" (Mención: <@&{festive_role}>)"
    else:
        festive_status = lang_service.get_text("setup_disabled", lang)

    # Category 1: General & Idioma
    cat_general_title = lang_service.get_text("serverinfo_cat_general", lang)
    lbl_lang = lang_service.get_text("setup_label_language", lang)
    val_general = f"> 🌐 **{lbl_lang}:** {lang_name}"
    embed.add_field(name=cat_general_title, value=val_general, inline=False)

    # Category 2: Canales de Interacción
    cat_channels_title = lang_service.get_text("serverinfo_cat_channels", lang)
    lbl_welcome = lang_service.get_text("setup_label_welcome", lang)
    lbl_confess = lang_service.get_text("setup_label_confess", lang)
    lbl_logs = lang_service.get_text("setup_label_logs", lang)
    lbl_birthday = lang_service.get_text("setup_label_birthday", lang)
    
    val_channels = (
        f"> 👋 **{lbl_welcome}:** {fmt_ch(config.get('welcome_channel_id'))}\n"
        f"> 🤫 **{lbl_confess}:** {fmt_ch(config.get('confessions_channel_id'))}\n"
        f"> 🎂 **{lbl_birthday}:** {fmt_ch(config.get('birthday_channel_id'))}\n"
        f"> 📜 **{lbl_logs}:** {fmt_ch(config.get('logs_channel_id'))}"
    )
    embed.add_field(name=cat_channels_title, value=val_channels, inline=False)

    # Category 3: Roles & Utilidades
    cat_roles_title = lang_service.get_text("serverinfo_cat_roles", lang)
    lbl_autorole = lang_service.get_text("setup_label_autorole", lang)
    lbl_wordday_ch = lang_service.get_text("setup_label_wordday_ch", lang)
    lbl_wordday_role = lang_service.get_text("setup_label_wordday_role", lang)
    
    val_roles = (
        f"> 🎭 **{lbl_autorole}:** {fmt_role(config.get('autorole_id'))}\n"
        f"> 📖 **{lbl_wordday_ch}:** {fmt_ch(config.get('wordday_channel_id'))}\n"
        f"> 🏷️ **{lbl_wordday_role}:** {fmt_role(config.get('wordday_role_id'))}"
    )
    embed.add_field(name=cat_roles_title, value=val_roles, inline=False)

    # Category 4: Sistemas Activos
    cat_systems_title = lang_service.get_text("serverinfo_cat_systems", lang)
    lbl_chaos = lang_service.get_text("setup_label_chaos", lang)
    lbl_festivedays = lang_service.get_text("setup_label_festivedays", lang)
    
    val_systems = (
        f"> 🔫 **{lbl_chaos}:** {chaos_status}\n"
        f"> 🎉 **{lbl_festivedays}:** {festive_status}"
    )
    embed.add_field(name=cat_systems_title, value=val_systems, inline=False)

    # Category 5: Alertas de YouTube
    cat_alerts_title = lang_service.get_text("serverinfo_cat_alerts", lang)
    if stream_alerts:
        alert_lines = []
        for alert in stream_alerts:
            ch_mention = f"<#{alert['discord_channel_id']}>"
            role_mention = f" (Mención: <@&{alert['role_id']}>)" if alert['role_id'] else ""
            msg_label = lang_service.get_text("setup_streamalert_msg_label", lang)
            custom_msg_val = f"\n  * {msg_label}: *\"{alert['custom_message']}\"*" if alert.get('custom_message') else ""
            alert_lines.append(f"> 🎥 **YouTube:** `{alert['channel_name']}` ➡️ {ch_mention}{role_mention}{custom_msg_val}")
        alerts_desc = "\n".join(alert_lines)
    else:
        lbl_streamalerts = lang_service.get_text("setup_label_streamalerts", lang)
        alerts_desc = f"> 🎥 **{lbl_streamalerts}:** {lang_service.get_text('setup_disabled', lang)}"
    
    embed.add_field(name=cat_alerts_title, value=alerts_desc, inline=False)

    return embed

class ServerInfoView(discord.ui.View):
    def __init__(self, guild: discord.Guild, config: dict, stats: dict, stream_alerts: list, lang: str, author_id: int):
        super().__init__(timeout=settings.GLOBAL_TIMEOUT)
        self.guild = guild
        self.config = config
        self.stats = stats
        self.stream_alerts = stream_alerts
        self.lang = lang
        self.author_id = author_id
        self.message = None

        self.btn_general.label = lang_service.get_text("serverinfo_tab_general", lang)
        self.btn_stats.label = lang_service.get_text("serverinfo_tab_stats", lang)
        self.btn_config.label = lang_service.get_text("serverinfo_tab_config", lang)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                lang_service.get_text("dev_interaction_error", self.lang), ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    async def _update(self, interaction: discord.Interaction, embed: discord.Embed, button_idx: int):
        buttons = [self.btn_general, self.btn_stats, self.btn_config]
        for i, btn in enumerate(buttons):
            btn.style = discord.ButtonStyle.primary if i == button_idx else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def btn_general(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, get_serverinfo_general_embed(self.guild, self.stats, self.lang), 0)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, get_serverinfo_stats_embed(self.guild, self.stats, self.lang), 1)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def btn_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update(interaction, get_serverinfo_config_embed(self.guild, self.config, self.stream_alerts, self.lang), 2)

def get_translate_embed(orig: str, trans: str, lang: str) -> discord.Embed:
    limit = settings.UI_CONFIG["MSG_PREVIEW_TRUNCATE"]
    txt = lang_service.get_text("trans_result", lang, orig=orig[:limit]+"...", trans=trans)
    return embed_service.success(lang_service.get_text("title_translate", lang), txt)