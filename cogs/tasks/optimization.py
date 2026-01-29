from discord.ext import commands, tasks
from services import db_service

class OptimizationTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache_flush_loop.start()

    def cog_unload(self):
        self.cache_flush_loop.cancel()

    @tasks.loop(seconds=60)
    async def cache_flush_loop(self):
        """Vuelca la RAM al Disco cada 60 segundos."""
        try:
            await db_service.flush_xp_cache()
        except Exception as e:
            print(f"⚠️ Error guardando XP caché: {e}")

    @cache_flush_loop.before_loop
    async def before_flush(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(OptimizationTasks(bot))