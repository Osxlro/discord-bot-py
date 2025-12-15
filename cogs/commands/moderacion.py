import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from services import embed_service, lang_service

class Moderacion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="clear", description= "Borra 'n' cantidad de mensajes.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, cantidad: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        max_msg = settings.CONFIG.get("moderation_config", {}).get("max_clear_msg", 100)

        if cantidad > max_msg:
            await ctx.reply(embed=embed_service.error("Error", f"Max: {max_msg}"), ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=cantidad)
        
        title = lang_service.get_text("clear_success", lang)
        desc = lang_service.get_text("clear_desc", lang, count=len(deleted))
        await ctx.send(embed=embed_service.success(title, desc))

    @commands.hybrid_command(name="kick", description="Expulsa un usuario.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, usuario: discord.Member, razon: str = "N/A"):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if usuario.id == ctx.author.id:
            await ctx.reply(lang_service.get_text("error_self_action", lang), ephemeral=True)
            return

        try:
            await usuario.kick(reason=razon)
            title = lang_service.get_text("kick_title", lang)
            desc = lang_service.get_text("kick_desc", lang, user=usuario.name, reason=razon)
            await ctx.reply(embed=embed_service.success(title, desc))
        except discord.Forbidden:
            await ctx.reply(lang_service.get_text("error_hierarchy", lang), ephemeral=True)
            
    @commands.hybrid_command(name="ban", description="Banea a un miembro permanentemente")
    @app_commands.describe(usuario="El usuario a banear", razon="Motivo")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, usuario: discord.Member, razon: str = "N/A"):
        lang = await lang_service.get_guild_lang(ctx.guild.id)

        if usuario.id == ctx.author.id:
            await ctx.reply(lang_service.get_text("error_self_action", lang), ephemeral=True)
            return

        try:
            await usuario.ban(reason=razon)
            title = lang_service.get_text("ban_title", lang)
            desc = lang_service.get_text("ban_desc", lang, user=usuario.name, reason=razon)
            await ctx.reply(embed=embed_service.success(title, desc))
        except discord.Forbidden:
            await ctx.reply(lang_service.get_text("error_hierarchy", lang), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderacion(bot))