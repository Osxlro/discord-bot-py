import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from services.features import moderation_service

from services.core import db_service, lang_service
from services.utils import embed_service, pagination_service

class Moderacion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="clear", description="Borra mensajes del chat.")
    @app_commands.describe(cantidad="Número de mensajes")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, cantidad: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        # Usamos .get() de forma segura desde settings
        max_msg = settings.CONFIG.get("moderation_config", {}).get("max_clear_msg", 100)

        if cantidad > max_msg:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("clear_limit", lang, max=max_msg), lite=True), ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        embed, error = await moderation_service.handle_clear(ctx.channel, cantidad, lang)
        if error:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_info", lang), error, lite=True), ephemeral=True)
        
        delete_after = settings.CONFIG.get("moderation_config", {}).get("delete_after", 5)
        await ctx.send(embed=embed, delete_after=delete_after)

    @commands.hybrid_command(name="timeout", description="Aísla (Timeout) a un usuario.")
    @app_commands.describe(usuario="Miembro", tiempo="Ej: 10m, 1h", razon="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, usuario: discord.Member, tiempo: str, razon: str = None):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        razon = razon or lang_service.get_text("mod_reason_default", lang)
        embed, error = await moderation_service.handle_timeout(ctx.author, usuario, tiempo, razon, lang)
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)
    
    @commands.hybrid_command(name="untimeout", description="Retira el aislamiento.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, usuario: discord.Member):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed, error = await moderation_service.handle_untimeout(usuario, lang)
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="kick", description="Expulsa a un miembro.")
    @app_commands.describe(usuario="Miembro", razon="Motivo")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, usuario: discord.Member, razon: str = None):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        razon = razon or lang_service.get_text("mod_reason_default", lang)
        embed, error = await moderation_service.handle_kick(ctx.author, usuario, razon, lang)
        if error:
            title = lang_service.get_text("title_info", lang) if "self" in error else lang_service.get_text("title_error", lang)
            return await ctx.reply(embed=embed_service.error(title, error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)
            
    @commands.hybrid_command(name="ban", description="Banea a un miembro.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, usuario: discord.Member, razon: str = None):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        razon = razon or lang_service.get_text("mod_reason_default", lang)
        embed, error = await moderation_service.handle_ban(ctx.author, usuario, razon, lang)
        if error:
            title = lang_service.get_text("title_info", lang) if "self" in error else lang_service.get_text("title_error", lang)
            return await ctx.reply(embed=embed_service.error(title, error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="warn", description="Advierte a un miembro.")
    @app_commands.describe(usuario="Miembro", razon="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, usuario: discord.Member, razon: str = None):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        razon = razon or lang_service.get_text("mod_reason_default", lang)
        embed, error = await moderation_service.handle_warn(ctx.author, usuario, razon, lang)
        if error:
            title = lang_service.get_text("title_info", lang) if "self" in error else lang_service.get_text("title_error", lang)
            return await ctx.reply(embed=embed_service.error(title, error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="warns", description="Muestra las advertencias de un usuario.")
    @app_commands.describe(usuario="Miembro")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def list_warns(self, ctx: commands.Context, usuario: discord.Member):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        pages, error = await moderation_service.handle_list_warns(ctx.guild, usuario, lang)
        
        if error:
            return await ctx.reply(embed=embed_service.info(lang_service.get_text("title_info", lang), error, lite=True))

        if len(pages) == 1:
            await ctx.reply(embed=pages[0])
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.send(embed=pages[0], view=view)

    @commands.hybrid_command(name="clearwarns", description="Limpia las advertencias de un usuario.")
    @app_commands.describe(usuario="Miembro")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_warns(self, ctx: commands.Context, usuario: discord.Member):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await moderation_service.handle_clear_warns(ctx.guild.id, usuario, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="delwarn", description="Elimina una advertencia específica por su ID.")
    @app_commands.describe(id="ID de la advertencia")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def delwarn(self, ctx: commands.Context, id: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed, error = await moderation_service.handle_delwarn(ctx.guild.id, id, lang)
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderacion(bot))