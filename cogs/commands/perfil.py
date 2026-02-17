import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services.features import profile_service
from services.core import lang_service

class Perfil(commands.Cog):
    """
    Cog encargado de la gestión y visualización de perfiles de usuario.
    Permite a los usuarios ver su tarjeta de estadísticas, personalizar su biografía
    y configurar mensajes especiales para eventos.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="profile", description="Gestión de perfil de usuario.", fallback="check")
    @app_commands.describe(usuario="El usuario del que quieres ver el perfil (vacío para ver el tuyo)")
    async def perfil(self, ctx: commands.Context, usuario: discord.Member = None):
        """Muestra la tarjeta de perfil con estadísticas globales y del servidor."""
        target = usuario or ctx.author
        # Obtener el idioma configurado para el servidor
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # El servicio orquesta la obtención de datos de múltiples tablas (users, guild_stats)
        # y solicita a la UI la construcción del embed final.
        embed = await profile_service.handle_profile(ctx.guild, target, lang)
        await ctx.reply(embed=embed)

    @perfil.command(name="desc", description="Cambia la biografía de tu tarjeta.")
    @app_commands.describe(texto="Máximo 200 caracteres.")
    async def set_desc(self, ctx: commands.Context, texto: str):
        """Actualiza la biografía que se muestra en la tarjeta de perfil."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # El servicio valida la longitud del texto y realiza el UPSERT en la base de datos
        embed, error = await profile_service.handle_update_description(ctx.author.id, texto, lang)
        
        if error:
            # Si el texto excede el límite definido en settings, se informa al usuario
            return await ctx.reply(error, ephemeral=True)
        
        await ctx.reply(embed=embed)

    @perfil.command(name="message", description="Personaliza tus mensajes de nivel o cumpleaños.")
    @app_commands.describe(
        tipo="¿Qué mensaje quieres personalizar?",
        texto="Tu mensaje. Usa {user}, {level} (solo nivel). Escribe 'reset' para borrar."
    )
    async def set_personal_msg(self, ctx: commands.Context, tipo: Literal["Nivel", "Cumpleaños"], texto: str):
        """Configura un mensaje personalizado para cuando el usuario sube de nivel o cumple años."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # El servicio maneja la lógica de 'reset' y actualiza la columna correspondiente en la DB
        embed = await profile_service.handle_update_personal_message(ctx.author.id, tipo, texto, lang)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    """Función de entrada para cargar el Cog en el bot."""
    await bot.add_cog(Perfil(bot))