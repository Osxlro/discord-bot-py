import discord
from discord.ext import commands, tasks
import datetime
import logging
from services.core import db_service, lang_service
from services.utils import embed_service

logger = logging.getLogger(__name__)

HOLIDAYS = {
    "01-01": "new_year",
    "14-02": "valentine",
    "31-10": "halloween",
    "24-12": "christmas_eve",
    "25-12": "christmas",
    "31-12": "new_years_eve"
}

class FestiveDaysTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.festive_check_loop.start()

    def cog_unload(self):
        self.festive_check_loop.cancel()

    @tasks.loop(hours=1.0)
    async def festive_check_loop(self):
        """Verifica cada hora si hoy es un día festivo para anunciarlo en los servidores configurados."""
        try:
            now = datetime.datetime.now()
            date_str = now.strftime("%d-%m") # Formato DD-MM
            
            if date_str not in HOLIDAYS:
                return

            holiday_key = HOLIDAYS[date_str]
            year = now.year

            # Obtener todos los servidores que tienen activado el sistema
            configs = await db_service.fetch_all(
                "SELECT guild_id, festivedays_channel_id, festivedays_role_id, language FROM guild_config WHERE festivedays_enabled = 1"
            )
            
            for conf in configs:
                guild_id = conf["guild_id"]
                channel_id = conf["festivedays_channel_id"]
                role_id = conf["festivedays_role_id"]
                lang = conf["language"] or "es"

                # Clave única para evitar notificar varias veces al día
                persistence_key = f"{guild_id}:{year}:{holiday_key}"
                
                # Comprobar si ya se envió hoy
                already_sent = await db_service.fetch_one(
                    "SELECT 1 FROM bot_persistence WHERE namespace = ? AND key = ?",
                    ("festive_days", persistence_key)
                )
                if already_sent:
                    continue

                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue

                channel = guild.get_channel(channel_id)
                if not channel:
                    continue

                # Preparar mención y textos traducidos
                role_mention = ""
                if role_id:
                    role = guild.get_role(role_id)
                    if role:
                        role_mention = role.mention

                title = lang_service.get_text(f"festive_title_{holiday_key}", lang)
                desc = lang_service.get_text(f"festive_desc_{holiday_key}", lang)

                # Si no existe la traducción, usamos fallback genérico
                if title == f"festive_title_{holiday_key}":
                    title = "🎉 ¡Día Especial!"
                if desc == f"festive_desc_{holiday_key}":
                    desc = f"¡Hoy celebramos {holiday_key.replace('_', ' ').title()}! 🎉 Que tengas un excelente día."

                embed = embed_service.info(title, desc)
                
                try:
                    content = f"{role_mention} 🎉" if role_mention else "🎉"
                    await channel.send(content=content, embed=embed)
                    
                    # Registrar que ya se envió para este servidor
                    await db_service.execute(
                        "INSERT OR REPLACE INTO bot_persistence (namespace, key, data) VALUES (?, ?, ?)",
                        ("festive_days", persistence_key, b"1")
                    )
                    await db_service.commit()
                    logger.info(f"Anuncio festivo '{holiday_key}' enviado a guild {guild_id}")
                except discord.Forbidden:
                    logger.warning(f"Sin permisos para enviar anuncio festivo en canal {channel_id} de guild {guild_id}")
                except Exception as e:
                    logger.exception(f"Error enviando anuncio festivo a guild {guild_id}: {e}")

        except Exception as e:
            logger.exception(f"Error en bucle de días festivos: {e}")

    @festive_check_loop.before_loop
    async def before_festive_check_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(FestiveDaysTask(bot))
