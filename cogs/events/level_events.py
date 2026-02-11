import logging
import random
import discord
from discord.ext import commands
from config import settings
from services import db_service, lang_service, level_service

logger = logging.getLogger(__name__)

class LevelEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(
            1, 
            settings.XP_CONFIG["COOLDOWN"], 
            commands.BucketType.user
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: 
            return
        
        # Evitar dar XP por comandos
        prefix = await self.bot.get_prefix(message)
        if isinstance(prefix, list) and any(message.content.startswith(p) for p in prefix): return
        if isinstance(prefix, str) and message.content.startswith(prefix): return

        # Sistema de Cooldown
        bucket = self._cd.get_bucket(message)
        if bucket.update_rate_limit(): 
            return

        xp_ganada = random.randint(
            settings.XP_CONFIG["MIN_XP"], 
            settings.XP_CONFIG["MAX_XP"]
        )
        
        nuevo_nivel, subio_de_nivel = await db_service.add_xp(message.guild.id, message.author.id, xp_ganada)
        
        if subio_de_nivel:
            await level_service.notify_level_up(message.guild, message.author, nuevo_nivel, fallback_channel=message.channel)

async def setup(bot):
    await bot.add_cog(LevelEvents(bot))