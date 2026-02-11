import discord
from config import settings
from services import lang_service
from discord.ext import commands

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

    for name, cog in bot.cogs.items():
        cmds = cog.get_commands()
        if not cmds: continue
        if not any(not c.hidden for c in cmds): continue

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
    cogs_count = len(bot.cogs)
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
    
    cats = [f"• {name}" for name in bot.cogs.keys() if bot.get_cog(name).get_commands()]
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