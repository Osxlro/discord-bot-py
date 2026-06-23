import datetime
import logging
from discord.ext import commands, tasks
from services.features import wordday_service

logger = logging.getLogger(__name__)

def get_mexico_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/Mexico_City")
    except Exception as e:
        logger.warning(f"No se pudo cargar la zona horaria America/Mexico_City ({e}). Usando UTC-6 como fallback.")
        return datetime.timezone(datetime.timedelta(hours=-6))

class WordDayTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_phrase.start()

    def cog_unload(self):
        self.daily_phrase.cancel()

    # 6:00 AM en America/Mexico_City (Referencia Latinoamérica)
    @tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=get_mexico_tz()))
    async def daily_phrase(self):
        await self.bot.wait_until_ready()
        await wordday_service.post_wordday(self.bot)

async def setup(bot):
    await bot.add_cog(WordDayTask(bot))