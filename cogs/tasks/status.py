import discord
from discord.ext import commands, tasks
from services import db_service

class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.status_loop.start()

    def _get_type(self, text: str):
        text = text.lower()
        if text == "watching": return discord.ActivityType.watching
        if text == "listening": return discord.ActivityType.listening
        if text == "competing": return discord.ActivityType.competing
        return discord.ActivityType.playing

    @tasks.loop(minutes=2) # Cambia cada 2 minutos
    async def status_loop(self):
        await self.bot.wait_until_ready()
        
        # Obtenemos un estado aleatorio de la DB
        row = await db_service.fetch_one("SELECT type, text FROM bot_statuses ORDER BY RANDOM() LIMIT 1")
        
        if row:
            act_type = self._get_type(row['type'])
            await self.bot.change_presence(activity=discord.Activity(type=act_type, name=row['text']))

    def cog_unload(self):
        self.status_loop.cancel()

async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))