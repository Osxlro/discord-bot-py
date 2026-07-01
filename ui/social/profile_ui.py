import discord
from config import settings
from services.core import lang_service
from services.utils import embed_service
from services.utils.embed_service import NonVitalRenderError

def get_general_embed(target: discord.Member, user_data: dict, lang: str) -> discord.Embed:
    """Genera el embed de información general (global)."""
    user_dict = dict(user_data) if user_data else {}
    desc = user_dict.get('description') or lang_service.get_text("profile_desc", lang)
    cumple = user_dict.get('birthday') or lang_service.get_text("profile_no_bday", lang)
    
    title = lang_service.get_text("profile_title", lang, user=target.display_name)
    embed = discord.Embed(title=title, color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    
    embed.add_field(name=lang_service.get_text("profile_field_desc", lang), value=f"*{desc}*", inline=False)
    embed.add_field(name=lang_service.get_text("profile_field_bday", lang), value=f"{cumple}", inline=True)

    try:
        gender = user_dict.get('gender')
        if gender and gender != "none":
            gender_key = f"gender_{gender.lower()}"
            gender_val = lang_service.get_text(gender_key, lang)
            embed.add_field(name=lang_service.get_text("profile_field_gender", lang), value=gender_val, inline=True)
    except Exception as e:
        raise NonVitalRenderError(embed, e, "gender")

    badges_str = user_dict.get("badges_str")
    if badges_str:
        embed.add_field(name=lang_service.get_text("profile_field_badges", lang), value=badges_str, inline=True)

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

def get_wallet_embed(target: discord.Member, user_data: dict, lang: str) -> discord.Embed:
    """Genera el embed del sistema de billetera (efectivo y banco)."""
    user_dict = dict(user_data) if user_data else {}
    coins = user_dict.get('coins') or 0
    bank_coins = user_dict.get('bank_coins') or 0
    
    title = lang_service.get_text("profile_wallet_title", lang) or "Billetera"
    embed = discord.Embed(title=f"{title} - {target.display_name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)

    cash_label = lang_service.get_text("profile_wallet_cash", lang) or "💵 Efectivo"
    bank_label = lang_service.get_text("profile_wallet_bank", lang) or "🏦 Cuenta de Banco"
    total_label = lang_service.get_text("profile_wallet_total", lang) or "💳 Total Neto"
    protected_label = lang_service.get_text("profile_wallet_protected", lang) or "Protegido por el Sistema"

    embed.add_field(name=cash_label, value=f"`{coins}` coins", inline=True)
    embed.add_field(name=bank_label, value=f"`{bank_coins}` coins\n*({protected_label})*", inline=True)
    embed.add_field(name=total_label, value=f"`{coins + bank_coins}` coins", inline=False)
    
    return embed

def get_inventory_embed(target: discord.Member, inventory_resolved: list[dict], lang: str) -> discord.Embed:
    """Genera el embed de visualización del inventario del usuario."""
    title = lang_service.get_text("profile_inventory_title", lang) or "Inventario"
    embed = discord.Embed(title=f"{title} - {target.display_name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)

    desc = ""
    if inventory_resolved:
        for item in inventory_resolved:
            emoji = item.get("emoji") or ""
            name = item.get("name") or ""
            qty = item.get("quantity") or 0
            desc += f"> **{emoji} {name}** — x{qty}\n"
    else:
        desc = lang_service.get_text("profile_inventory_empty", lang) or "🎒 Tu inventario está vacío."

    embed.description = desc
    return embed

def get_others_embed(target: discord.Member, user_data: dict, lang: str) -> discord.Embed:
    """Genera el embed de previsualización de mensajes personalizados y configuraciones varias (prefijo)."""
    user_dict = dict(user_data) if user_data else {}
    prefix = user_dict.get('custom_prefix') or settings.CONFIG["bot_config"]["prefix"]
    
    title = lang_service.get_text("profile_select_others", lang) or "Otros Ajustes"
    embed = discord.Embed(title=f"{title} - {target.display_name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)

    embed.add_field(
        name=lang_service.get_text("profile_field_prefix", lang),
        value=f"`{prefix}`",
        inline=False
    )

    limit = settings.UI_CONFIG["MSG_PREVIEW_TRUNCATE"]
    lvl_msg = user_dict.get('personal_level_msg')
    bday_msg = user_dict.get('personal_birthday_msg')

    lvl_msg_val = f"\"{lvl_msg[:limit]}...\"" if lvl_msg else lang_service.get_text("log_none", lang)
    bday_msg_val = f"\"{bday_msg[:limit]}...\"" if bday_msg else lang_service.get_text("log_none", lang)

    embed.add_field(
        name=lang_service.get_text("profile_preview_lvl_label", lang) or "Mensaje de Nivel",
        value=lvl_msg_val,
        inline=True
    )
    embed.add_field(
        name=lang_service.get_text("profile_preview_bday_label", lang) or "Mensaje de Cumpleaños",
        value=bday_msg_val,
        inline=True
    )
    
    return embed

class ProfileDropdown(discord.ui.Select):
    def __init__(self, is_dm: bool, lang: str):
        options = [
            discord.SelectOption(
                label=lang_service.get_text("profile_select_general", lang) or "Información General",
                value="general",
                emoji="👤"
            )
        ]
        if not is_dm:
            options.append(discord.SelectOption(
                label=lang_service.get_text("profile_select_stats", lang) or "Estadísticas del Servidor",
                value="stats",
                emoji="📊"
            ))
        options.append(discord.SelectOption(
            label=lang_service.get_text("profile_select_wallet", lang) or "Billetera",
            value="wallet",
            emoji="💳"
        ))
        options.append(discord.SelectOption(
            label=lang_service.get_text("profile_select_inventory", lang) or "Inventario",
            value="inventory",
            emoji="🎒"
        ))
        options.append(discord.SelectOption(
            label=lang_service.get_text("profile_select_others", lang) or "Otros Ajustes",
            value="others",
            emoji="⚙️"
        ))

        placeholder = lang_service.get_text("profile_select_placeholder", lang) or "Selecciona una sección..."
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        view = self.view
        
        if selection == "general":
            embed = get_general_embed(view.target, view.user_data, view.lang)
        elif selection == "stats":
            embed = get_stats_embed(view.target, view.guild_data, view.xp_next, view.lang)
        elif selection == "wallet":
            embed = get_wallet_embed(view.target, view.user_data, view.lang)
        elif selection == "inventory":
            embed = get_inventory_embed(view.target, view.inventory_resolved, view.lang)
        else:
            embed = get_others_embed(view.target, view.user_data, view.lang)

        await interaction.response.edit_message(embed=embed, view=view)


class ProfileView(discord.ui.View):
    """Vista con un menú desplegable (Select) para navegar por las secciones del perfil."""
    def __init__(self, target, user_data, guild_data, xp_next, inventory_resolved, lang, author_id, is_dm: bool = False):
        super().__init__(timeout=settings.GLOBAL_TIMEOUT)
        self.target = target
        self.user_data = user_data
        self.guild_data = guild_data
        self.xp_next = xp_next
        self.inventory_resolved = inventory_resolved
        self.lang = lang
        self.author_id = author_id
        self.message = None

        self.add_item(ProfileDropdown(is_dm, lang))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(lang_service.get_text("dev_interaction_error", self.lang), ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass

def get_profile_embed(target: discord.Member, user_data: dict, guild_data: dict, xp_next: int, lang: str) -> discord.Embed:
    """Mantiene compatibilidad con el wrapper de servicio (retorna la vista general)."""
    return get_general_embed(target, user_data, lang)

def get_profile_update_success_embed(lang: str, type_key: str) -> discord.Embed:
    """Genera un embed de éxito para actualizaciones de perfil."""
    title = lang_service.get_text("profile_update_success", lang)
    desc = lang_service.get_text(type_key, lang)
    return embed_service.success(title, desc, lite=True)