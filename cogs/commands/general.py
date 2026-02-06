import discord
import logging
from discord import app_commands
from discord.ext import commands
from services import embed_service, translator_service, lang_service, db_service

logger = logging.getLogger(__name__)

EMOJI_MAP = {
    "General": "💡", "Moderacion": "🛡️", "Niveles": "📊",
    "Diversion": "🎲", "Configuracion": "⚙️", "Developer": "💻",
    "Cumpleanos": "🎂", "Roles": "🎭", "Voice": "🎙️", 
    "Perfil": "👤", "Status": "🟢", "Backup": "💾",
    "Usuario": "👤", "Minecraft": "🧱", "Music": "🎵"
}

class HelpSelect(discord.ui.Select):
    def __init__(self, bot, ctx, lang):
        self.bot = bot
        self.ctx = ctx
        self.lang = lang
        
        options = [
            discord.SelectOption(
                label=lang_service.get_text("help_home", lang),
                description=lang_service.get_text("help_home_desc", lang),
                value="home",
                emoji="🏠"
            )
        ]

        for name, cog in bot.cogs.items():
            cmds = cog.get_commands()
            if not cmds: continue
            if not any(not c.hidden for c in cmds): continue

            desc_key = f"help_desc_{name.lower()}"
            description = lang_service.get_text(desc_key, lang)
            if description == desc_key: description = f"Comandos de {name}."

            options.append(discord.SelectOption(
                label=name,
                description=description[:100],
                value=name,
                emoji=EMOJI_MAP.get(name, "📂")
            ))

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
            embed = await General.get_home_embed(self.ctx)
            await interaction.response.edit_message(embed=embed)
        else:
            cog = self.bot.get_cog(value)
            if not cog: return
            
            title = lang_service.get_text("help_module_title", self.lang, module=value)
            module_desc = lang_service.get_text("help_module_desc", self.lang, module=value)
            
            embed = discord.Embed(
                title=f"{EMOJI_MAP.get(value, '📂')} {title}",
                description=f"*{module_desc}*\n\n",
                color=self.ctx.guild.me.color if self.ctx.guild else discord.Color.blurple()
            )

            cmds_list = []
            for cmd in cog.get_commands():
                if cmd.hidden: continue
                
                if isinstance(cmd, (commands.HybridGroup, commands.Group)):
                    for sub in cmd.commands:
                        desc_cmd = sub.description or sub.short_doc or "..."
                        cmds_list.append(f"**/{cmd.name} {sub.name}**\n> └ {desc_cmd}")
                else:
                    desc_cmd = cmd.description or cmd.short_doc or "..."
                    cmds_list.append(f"**/{cmd.name}**\n> └ {desc_cmd}")

            embed.description += "\n".join(cmds_list) if cmds_list else lang_service.get_text("help_no_cmds", self.lang)
            embed.set_footer(text=f"Total: {len(cmds_list)} comandos", icon_url=self.bot.user.display_avatar.url)

            await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot, ctx, lang):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot, ctx, lang))

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(name="Traducir", callback=self.traducir_mensaje)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @staticmethod
    async def get_home_embed(ctx):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        cogs_count = len(ctx.bot.cogs)
        total_cmds = len([c for c in ctx.bot.commands if not c.hidden])
        
        title = lang_service.get_text("help_title", lang)
        desc = lang_service.get_text("help_desc", lang, user=ctx.author.display_name)
        stats = lang_service.get_text("help_stats", lang, cats=cogs_count, cmds=total_cmds)
        # Limpiamos el texto de stats para que se vea mejor
        stats = stats.replace("•", ">").replace("\n", "\n")
        
        embed = discord.Embed(
            title=f"✨ {title}",
            description=f"{desc}\n\n📊 **Estadísticas**\n{stats}",
            color=ctx.guild.me.color if ctx.guild else discord.Color.blurple()
        )
        
        cats = [f"• {name}" for name in ctx.bot.cogs.keys() if ctx.bot.get_cog(name).get_commands()]
        cats_formatted = "\n".join(cats)
        
        embed.add_field(name=f"{lang_service.get_text('help_categories', lang)}", value=f"```\n{cats_formatted}\n```", inline=False)
        embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
        embed.set_footer(text="Selecciona una categoría abajo 👇", icon_url=ctx.bot.user.display_avatar.url)
        
        return embed

    @commands.hybrid_command(name="help", description="Muestra el panel de ayuda y comandos.")
    async def help(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await self.get_home_embed(ctx)
        view = HelpView(self.bot, ctx, lang)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="ping", description="Muestra la latencia actual del bot.")
    async def ping(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        ms = round(self.bot.latency * 1000)
        
        txt = lang_service.get_text("ping_msg", lang, ms=ms)
        await ctx.reply(embed=embed_service.info(lang_service.get_text("title_ping", lang), txt, lite=True))

    @commands.hybrid_command(name="calc", description="Calculadora flexible. Ej: /calc + 5 10")
    @app_commands.describe(operacion="Usa símbolos (+, -, *, /)", num1="Primer número", num2="Segundo número")
    async def calc(self, ctx: commands.Context, operacion: str, num1: float, num2: float):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        op_map = {
            "sumar": "+", "suma": "+", "add": "+", "+": "+", "mas": "+",
            "restar": "-", "resta": "-", "minus": "-", "-": "-", "menos": "-",
            "multiplicacion": "*", "multiplicar": "*", "por": "*", "*": "*", "x": "*",
            "division": "/", "dividir": "/", "div": "/", "/": "/"
        }
        
        op_symbol = op_map.get(operacion.lower())
        
        if not op_symbol:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), "Operación no válida.\nUsa: `+`, `-`, `*`, `/`", lite=True), ephemeral=True)
            return
        
        try:
            res = 0
            if op_symbol == "+": res = num1 + num2
            elif op_symbol == "-": res = num1 - num2
            elif op_symbol == "*": res = num1 * num2
            elif op_symbol == "/":
                if num2 == 0: raise ValueError("No puedes dividir por cero.")
                res = round(num1 / num2, 2)

            txt = lang_service.get_text("calc_result", lang, a=num1, op=op_symbol, b=num2, res=res)
            await ctx.reply(embed=embed_service.success(lang_service.get_text("title_math", lang), txt))
            
        except ValueError as e:
            logger.warning(f"Error Calc ({ctx.author}): {e}")
            txt = lang_service.get_text("calc_error", lang, error=str(e))
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), txt, lite=True))

    @commands.hybrid_command(name="serverinfo", description="Muestra información y configuración del servidor.")
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
        await ctx.defer()
        
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        config = await db_service.get_guild_config(ctx.guild.id)
        guild = ctx.guild
        
        # Helper para formatear canales/roles (Muestra ❌ si no está configurado)
        def fmt(val, type_):
            if not val: return "❌"
            return f"<#{val}>" if type_ == "ch" else f"<@&{val}>"

        # Cálculo de estadísticas
        # Nota: guild.members requiere intents de miembros activados para ser exacto
        humans = len([m for m in guild.members if not m.bot])
        bots = guild.member_count - humans
        
        title = lang_service.get_text("serverinfo_title", lang, name=guild.name)
        
        embed = discord.Embed(title=title, color=guild.me.color)
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        if guild.banner: embed.set_image(url=guild.banner.url)

        # Campo 1: Información General
        embed.add_field(name=lang_service.get_text("serverinfo_owner", lang), value=f"<@{guild.owner_id}>", inline=True)
        embed.add_field(name=lang_service.get_text("serverinfo_id", lang), value=f"`{guild.id}`", inline=True)
        embed.add_field(name=lang_service.get_text("serverinfo_created", lang), value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)

        # Campo 2: Estadísticas
        stats_txt = lang_service.get_text("serverinfo_stats_desc", lang,
            total=guild.member_count, humans=humans, bots=bots,
            roles=len(guild.roles), boosts=guild.premium_subscription_count,
            channels=len(guild.channels), cats=len(guild.categories),
            text=len(guild.text_channels), voice=len(guild.voice_channels)
        )
        embed.add_field(name=lang_service.get_text("serverinfo_stats", lang), value=stats_txt, inline=False)

        # Campo 3: Configuración del Bot
        lang_name = "Español 🇪🇸" if config.get("language") == "es" else "English 🇺🇸"
        conf_txt = lang_service.get_text("serverinfo_conf_desc", lang,
            language=lang_name,
            welcome=fmt(config.get("welcome_channel_id"), "ch"),
            confess=fmt(config.get("confessions_channel_id"), "ch"),
            logs=fmt(config.get("logs_channel_id"), "ch"),
            bday=fmt(config.get("birthday_channel_id"), "ch"),
            autorole=fmt(config.get("autorole_id"), "role")
        )
        embed.add_field(name=lang_service.get_text("serverinfo_config", lang), value=conf_txt, inline=False)

        await ctx.send(embed=embed)

    async def traducir_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        lang = await lang_service.get_guild_lang(interaction.guild_id)
        await interaction.response.defer(ephemeral=True)
        
        try:
            res = await translator_service.traducir(message.content, "es")
            txt = lang_service.get_text("trans_result", lang, orig=message.content[:50]+"...", trans=res['traducido'])
            await interaction.followup.send(embed=embed_service.success(lang_service.get_text("title_translate", lang), txt), ephemeral=True)
        except Exception as e:
            logger.error(f"Error Traductor: {e}")
            await interaction.followup.send(embed=embed_service.error(lang_service.get_text("title_error", lang), str(e), lite=True), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))