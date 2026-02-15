import datetime
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from services.features import wordday_service

class WordDayTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_phrase.start()

    def cog_unload(self):
        self.daily_phrase.cancel()

    # 6:00 AM en America/Mexico_City (Referencia Latinoamérica)
    @tasks.loop(time=datetime.time(hour=6, minute=0, tzinfo=ZoneInfo("America/Mexico_City")))
    async def daily_phrase(self):
        await self.bot.wait_until_ready()
        await wordday_service.post_wordday(self.bot)

async def setup(bot):
    await bot.add_cog(WordDayTask(bot))