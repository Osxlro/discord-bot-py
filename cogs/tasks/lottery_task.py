import logging
from discord.ext import commands, tasks
from services.features import lottery_service

logger = logging.getLogger(__name__)

class LotteryTask(commands.Cog):
    """Tarea en segundo plano para sortear la lotería diaria."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.draw_lottery.start()

    def cog_unload(self):
        self.draw_lottery.cancel()

    @tasks.loop(hours=24)
    async def draw_lottery(self):
        """Bucle diario para seleccionar el ganador de la lotería."""
        await self.bot.wait_until_ready()
        logger.info("🎟️ [LotteryTask] Iniciando sorteo diario de lotería...")
        try:
            await lottery_service.draw_daily_lottery(self.bot)
        except Exception as e:
            logger.exception(f"❌ [LotteryTask] Error inesperado durante el sorteo: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(LotteryTask(bot))
