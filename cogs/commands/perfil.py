import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import db_service, embed_service, lang_service, profile_service
from config import settings

class Perfil(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="perfil", description="Gestión de perfil de usuario.", fallback="ver")
    @app_commands.describe(usuario="El usuario del que quieres ver el perfil (vacío para ver el tuyo)")
    async def perfil(self, ctx: commands.Context, usuario: discord.Member = None):
        target = usuario or ctx.author
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        embed = await profile_service.get_profile_embed(self.bot, ctx.guild, target, lang)
        await ctx.reply(embed=embed)

    @perfil.command(name="descripcion", description="Cambia la biografía de tu tarjeta.")
    @app_commands.describe(texto="Máximo 200 caracteres.")
    async def set_desc(self, ctx: commands.Context, texto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if len(texto) > settings.UI_CONFIG["MAX_DESC_LENGTH"]: 
            await ctx.reply(lang_service.get_text("error_max_chars", lang, max=settings.UI_CONFIG["MAX_DESC_LENGTH"]), ephemeral=True)
            return
        
        await profile_service.update_description(ctx.author.id, texto)
        await ctx.reply(embed=embed_service.success(lang_service.get_text("profile_update_success", lang), lang_service.get_text("profile_desc_saved", lang), lite=True))

    @perfil.command(name="mensaje", description="Personaliza tus mensajes de nivel o cumpleaños.")
    @app_commands.describe(
        tipo="¿Qué mensaje quieres personalizar?",
        texto="Tu mensaje. Usa {user}, {level} (solo nivel). Escribe 'reset' para borrar."
    )
    async def set_personal_msg(self, ctx: commands.Context, tipo: Literal["Nivel", "Cumpleaños"], texto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        await profile_service.update_personal_message(ctx.author.id, tipo, texto)
        await ctx.reply(embed=embed_service.success(lang_service.get_text("profile_update_success", lang), lang_service.get_text("profile_msg_saved", lang), lite=True))

async def setup(bot: commands.Bot):
    await bot.add_cog(Perfil(bot))