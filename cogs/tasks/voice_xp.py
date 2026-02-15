from discord.ext import commands, tasks
from services import db_service, level_service
from config import settings
import logging

logger = logging.getLogger(__name__)

class VoiceXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_xp_loop.start()

    def cog_unload(self):
        self.voice_xp_loop.cancel()

    @tasks.loop(seconds=settings.XP_CONFIG["VOICE_INTERVAL"])
    async def voice_xp_loop(self):
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                if len(channel.members) < 2: continue
                if guild.afk_channel and channel.id == guild.afk_channel.id: continue

                for member in channel.members:
                    if member.bot: continue
                    if member.voice.self_mute or member.voice.self_deaf or member.voice.deaf: continue

                    try:
                        nuevo_nivel, subio = await db_service.add_xp(
                            guild.id, 
                            member.id, 
                            settings.XP_CONFIG["VOICE_AMOUNT"]
                        )
                        
                        if subio:
                            await level_service.notify_level_up(guild, member, nuevo_nivel, fallback_channel=channel)
                            
                    except Exception:
                        logger.exception(f"Error VoiceXP en {guild.name}")

async def setup(bot):
    await bot.add_cog(VoiceXP(bot))