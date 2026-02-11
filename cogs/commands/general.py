import discord
import logging
from discord import app_commands
from discord.ext import commands
from config.locales import LOCALES
from services import embed_service, translator_service, lang_service, db_service, help_service
from config import settings

logger = logging.getLogger(__name__)

class HelpSelect(discord.ui.Select):
    def __init__(self, bot, ctx, lang):
        self.bot = bot
        self.ctx = ctx
        self.lang = lang
        
        options = help_service.get_help_options(bot, lang)
        
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
            embed = await help_service.get_home_embed(self.bot, self.ctx.guild, self.ctx.author, self.lang)
            await interaction.response.edit_message(embed=embed)
        else:
            embed = help_service.get_module_embed(self.bot, value, self.ctx.guild, self.lang)
            await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot, ctx, lang):
        super().__init__(timeout=settings.TIMEOUT_CONFIG["HELP"])
        self.add_item(HelpSelect(bot, ctx, lang))

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Nota: El nombre del menú contextual se define en español por defecto o desde locales
        self.ctx_menu = app_commands.ContextMenu(name=LOCALES["es"]["ctx_menu_translate"], callback=self.traducir_mensaje)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.hybrid_command(name="help", description="Muestra el panel de ayuda y comandos.")
    async def help(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await help_service.get_home_embed(self.bot, ctx.guild, ctx.author, lang)
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
        
        op_symbol = settings.MATH_CONFIG["OP_MAP"].get(operacion.lower())
        
        if not op_symbol:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), "Operación no válida.\nUsa: `+`, `-`, `*`, `/`", lite=True), ephemeral=True)
            return
        
        try:
            res = 0
            if op_symbol == "+": res = num1 + num2
            elif op_symbol == "-": res = num1 - num2
            elif op_symbol == "*": res = num1 * num2
            elif op_symbol == "/":
                if num2 == 0: raise ValueError(lang_service.get_text("math_div_zero", lang))
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
            if not val: return lang_service.get_text("serverinfo_not_set", lang)
            return f"<#{val}>" if type_ == "ch" else f"<@&{val}>"

        # Cálculo de estadísticas
        # Nota: guild.members requiere intents de miembros activados para ser exacto
        # Optimización: Si hay muchos miembros, evitamos la iteración pesada
        if guild.member_count > settings.GENERAL_CONFIG["LARGE_SERVER_THRESHOLD"]:
            na = lang_service.get_text("serverinfo_na", lang)
            humans, bots = na, na # Ahorramos CPU en servidores grandes
        else:
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
        lang_name = lang_service.get_text("lang_name_es", lang) if config.get("language") == "es" else lang_service.get_text("lang_name_en", lang)
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
            limit = settings.UI_CONFIG["MSG_PREVIEW_TRUNCATE"]
            res = await translator_service.traducir(message.content, settings.GENERAL_CONFIG["DEFAULT_LANG"])
            txt = lang_service.get_text("trans_result", lang, orig=message.content[:limit]+"...", trans=res['traducido'])
            await interaction.followup.send(embed=embed_service.success(lang_service.get_text("title_translate", lang), txt), ephemeral=True)
        except Exception as e:
            logger.error(f"Error Traductor: {e}")
            await interaction.followup.send(embed=embed_service.error(lang_service.get_text("title_error", lang), str(e), lite=True), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))