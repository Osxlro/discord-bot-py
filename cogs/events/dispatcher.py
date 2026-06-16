import logging
import discord
from discord.ext import commands
from services.core import db_service, lang_service

logger = logging.getLogger(__name__)

class EventDispatcher(commands.Cog):
    """
    Despachador centralizado de eventos on_message.
    Reduce consultas redundantes de base de datos e I/O innecesarios de Discord.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Filtros rápidos iniciales (sin costo de DB/RAM)
        if message.author.bot or not message.guild or not message.content:
            return

        # 2. Única consulta estructurada (Caché optimizado)
        try:
            config = await db_service.get_guild_config(message.guild.id)
            lang = await lang_service.get_guild_lang(message.guild.id)
        except Exception:
            logger.exception("Error al recuperar configuración en dispatcher")
            return

        # 3. Invocar componentes independientes de forma segura
        
        # A. Procesamiento de XP de niveles
        level_cog = self.bot.get_cog("LevelEvents")
        if level_cog:
            try:
                await level_cog.process_message_xp(message, lang, config)
            except Exception:
                logger.exception("Error procesando XP en despachador")

        # B. Ruleta de Caos
        chaos_cog = self.bot.get_cog("Chaos")
        if chaos_cog:
            try:
                await chaos_cog.process_message_chaos(message, lang, config)
            except Exception:
                logger.exception("Error procesando ruleta de caos en despachador")

        # C. Menciones al Bot
        mencion_cog = self.bot.get_cog("Mencion")
        if mencion_cog:
            try:
                await mencion_cog.process_message_mention(message, lang, config)
            except Exception:
                logger.exception("Error procesando respuesta de mención en despachador")

async def setup(bot: commands.Bot):
    await bot.add_cog(EventDispatcher(bot))
