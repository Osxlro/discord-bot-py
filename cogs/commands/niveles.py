import logging
import discord
from discord import app_commands
from discord.ext import commands
from services.features import level_service
from services.core import lang_service
from services.utils import embed_service, pagination_service

logger = logging.getLogger(__name__)

class Niveles(commands.Cog):
    """
    Cog encargado del sistema de niveles, experiencia (XP) y prestigio (Rebirths).
    Permite a los usuarios consultar su progreso, ver el ranking del servidor
    y reiniciar su nivel para obtener beneficios de renacimiento.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="rank", description="Muestra el nivel, progreso y rebirths de un usuario.")
    @app_commands.describe(usuario="El usuario a consultar")
    async def rank(self, ctx: commands.Context, usuario: discord.Member = None):
        """Muestra una tarjeta informativa con el nivel actual, XP y barra de progreso."""
        target = usuario or ctx.author
        # Obtener el idioma configurado para el servidor
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Delegar la obtención de datos y generación del embed al servicio
        embed = await level_service.handle_rank(ctx.guild, target, lang)
        
        if not embed:
            # Si el usuario no tiene datos (no ha enviado mensajes), mostrar aviso
            msg = lang_service.get_text("rank_no_data", lang)
            return await ctx.reply(embed=embed_service.warning(
                lang_service.get_text("title_info", lang), msg, lite=True
            ))

        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="leaderboard", description="Muestra el top de XP del servidor")
    async def leaderboard(self, ctx: commands.Context):
        """Muestra el ranking de los usuarios con más experiencia en el servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # El servicio recupera los datos y genera las páginas de embeds para el ranking
        pages = await level_service.handle_leaderboard(ctx.guild, lang)

        if not pages:
            # Si nadie tiene XP aún en el servidor
            msg = lang_service.get_text("leaderboard_empty", lang)
            await ctx.reply(embed=embed_service.info(lang_service.get_text("title_empty", lang), msg))
            return

        if len(pages) == 1:
            await ctx.reply(embed=pages[0])
        else:
            # Usar el sistema de paginación si hay muchos usuarios en el top
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.reply(embed=pages[0], view=view)

    @commands.hybrid_command(name="rebirth", description="Reinicia tu nivel (requiere Nivel 100) para ganar un Rebirth.")
    async def rebirth(self, ctx: commands.Context):
        """Permite a un usuario de nivel 100 reiniciar su progreso a cambio de un punto de Rebirth."""
        # Diferir respuesta ya que la validación y actualización de DB puede tardar
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        # El servicio maneja la validación de nivel y la ejecución del renacimiento
        embed, _ = await level_service.handle_rebirth(ctx.guild.id, ctx.author.id, lang)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Función de entrada para cargar el Cog en el bot."""
    await bot.add_cog(Niveles(bot))