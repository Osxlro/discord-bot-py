import discord
from discord.ext import commands
from config import settings
from services.core import lang_service

def _get_visible_cogs(bot):
    """Retorna una lista de Cogs que tienen al menos un comando visible."""
    return [
        cog for cog in bot.cogs.values() 
        if any(not c.hidden for c in cog.get_commands())
    ]

def get_help_options(bot, lang: str) -> list[discord.SelectOption]:
    """Genera la lista de opciones para el menú desplegable de ayuda."""
    options = [
        discord.SelectOption(
            label=lang_service.get_text("help_home", lang),
            description=lang_service.get_text("help_home_desc", lang),
            value="home",
            emoji=settings.HELP_CONFIG["HOME_EMOJI"]
        )
    ]

    for cog in _get_visible_cogs(bot):
        name = cog.qualified_name
        desc_key = f"help_desc_{name.lower()}"
        description = lang_service.get_text(desc_key, lang)
        if description == desc_key: 
            description = lang_service.get_text("help_default_module_desc", lang, name=name)

        options.append(discord.SelectOption(
            label=name,
            description=description[:settings.UI_CONFIG["SELECT_DESC_TRUNCATE"]],
            value=name,
            emoji=settings.HELP_CONFIG["EMOJI_MAP"].get(name, "📂")
        ))
    return options

async def get_home_embed(bot, guild: discord.Guild, user: discord.Member, lang: str) -> discord.Embed:
    """Construye el embed principal de la ayuda."""
    visible_cogs = _get_visible_cogs(bot)
    cogs_count = len(visible_cogs)
    total_cmds = len([c for c in bot.commands if not c.hidden])
    
    title = lang_service.get_text("help_title", lang)
    desc = lang_service.get_text("help_desc", lang, user=user.display_name)
    stats = lang_service.get_text("help_stats", lang, cats=cogs_count, cmds=total_cmds)
    stats_title = lang_service.get_text("help_stats_title", lang)
    
    stats = stats.replace("•", ">")
    
    embed = discord.Embed(
        title=f"✨ {title}",
        description=f"{desc}\n\n{stats_title}\n{stats}",
        color=guild.me.color if guild else discord.Color.blurple()
    )
    
    cats = [f"• {cog.qualified_name}" for cog in visible_cogs]
    cats_formatted = "\n".join(cats)
    
    embed.add_field(name=f"{lang_service.get_text('help_categories', lang)}", value=f"```\n{cats_formatted}\n```", inline=False)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text=lang_service.get_text("help_home_footer", lang), icon_url=bot.user.display_avatar.url)
    
    return embed

def get_module_embed(bot, module_name: str, guild: discord.Guild, lang: str) -> discord.Embed:
    """Construye el embed detallado para un módulo específico."""
    cog = bot.get_cog(module_name)
    title = lang_service.get_text("help_module_title", lang, module=module_name)
    module_desc = lang_service.get_text("help_module_desc", lang, module=module_name)
    
    embed = discord.Embed(
        title=f"{settings.HELP_CONFIG['EMOJI_MAP'].get(module_name, '📂')} {title}",
        description=f"*{module_desc}*\n\n",
        color=guild.me.color if guild else discord.Color.blurple()
    )

    cmds_list = []
    for cmd in cog.get_commands():
        if cmd.hidden: continue
        
        desc_cmd = cmd.description or cmd.short_doc or "..."
        if isinstance(cmd, (commands.HybridGroup, commands.Group)):
            for sub in cmd.commands:
                cmds_list.append(f"**/{cmd.name} {sub.name}**\n> └ {sub.description or '...'}")
        else:
            cmds_list.append(f"**/{cmd.name}**\n> └ {desc_cmd}")

    embed.description += "\n".join(cmds_list) if cmds_list else lang_service.get_text("help_no_cmds", lang)
    embed.set_footer(text=lang_service.get_text("help_total_cmds", lang, count=len(cmds_list)), icon_url=bot.user.display_avatar.url)
    return embed

class HelpSelect(discord.ui.Select):
    def __init__(self, bot, ctx, lang):
        self.bot = bot
        self.ctx = ctx
        self.lang = lang
        
        options = get_help_options(bot, lang)
        
        super().__init__(
            placeholder=lang_service.get_text("help_placeholder", lang),
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                lang_service.get_text("error_self_action", self.lang), ephemeral=True
            )

        value = self.values[0]
        if value == "home":
            embed = await get_home_embed(self.bot, self.ctx.guild, self.ctx.author, self.lang)
        else:
            embed = get_module_embed(self.bot, value, self.ctx.guild, self.lang)
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot, ctx, lang):
        super().__init__(timeout=settings.TIMEOUT_CONFIG["HELP"])
        self.add_item(HelpSelect(bot, ctx, lang))