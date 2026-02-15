from discord.ext import commands, tasks
from services import birthday_service
from config import settings

class BirthdayTask(commands.Cog):
    """Tarea en segundo plano para la gestión de cumpleaños."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    @tasks.loop(hours=settings.BIRTHDAY_CONFIG["CHECK_INTERVAL_HOURS"])
    async def check_birthdays(self):
        """Bucle diario de felicitaciones."""
        await self.bot.wait_until_ready()
        await birthday_service.process_daily_birthdays(self.bot)

async def setup(bot: commands.Bot):
    await bot.add_cog(BirthdayTask(bot))