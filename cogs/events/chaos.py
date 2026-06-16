import datetime
import logging
import discord
from discord.ext import commands
from config import settings
from services.utils import embed_service
from services.core import db_service, lang_service
from services.utils import random_service

logger = logging.getLogger(__name__)

class Chaos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def update_local_config(self, guild_id: int, enabled: bool, prob: float):
        """Método obsoleto para mantener compatibilidad con setup_service."""
        pass

    async def process_message_chaos(self, message: discord.Message, lang: str, config: dict):
        """Procesa la ruleta de caos usando la configuración provista."""
        enabled = bool(config.get("chaos_enabled", 1))
        if not enabled:
            return

        prob = float(config.get("chaos_probability", 0.01))

        # Verificamos suerte
        if random_service.verificar_suerte(prob):
            try:
                # Timeout del usuario
                await message.author.timeout(datetime.timedelta(minutes=1), reason="Chaos Roulette")
                
                # Mensaje visual
                title = lang_service.get_text("chaos_title", lang)
                txt = lang_service.get_text("chaos_bang", lang, user=message.author.name, prob=int(prob*100))
                await message.channel.send(embed=embed_service.info(title, txt))
                logger.info(f"Chaos activado para {message.author} en {message.guild.name}")
            except discord.Forbidden:
                # Si el bot no tiene permisos, simplemente lo ignora para no spamear errores
                pass
            except Exception as e:
                logger.error(f"Error en Chaos: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Chaos(bot))