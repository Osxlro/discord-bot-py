import discord
from discord.ext import commands, tasks
from services import db_service, lang_service
from config import settings

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
                            await self._notificar_nivel(guild, channel, member, nuevo_nivel)
                            
                    except Exception as e:
                        print(f"Error VoiceXP en {guild.name}: {e}")

    async def _notificar_nivel(self, guild, channel, member, nuevo_nivel):
        try:
            lang = await lang_service.get_guild_lang(guild.id)
            config = await db_service.get_guild_config(guild.id)
            user_data = await db_service.fetch_one("SELECT personal_level_msg FROM users WHERE user_id = ?", (member.id,))
            
            if user_data and user_data['personal_level_msg']:
                msg_raw = user_data['personal_level_msg']
            elif config.get('server_level_msg'):
                msg_raw = config['server_level_msg']
            else:
                msg_raw = lang_service.get_text("level_up_default", lang)
            
            msg_final = msg_raw.replace("{user}", member.mention)\
                               .replace("{level}", str(nuevo_nivel))\
                               .replace("{server}", guild.name)

            dest_channel = None
            if config.get('logs_channel_id'):
                dest_channel = guild.get_channel(config['logs_channel_id'])
            
            if not dest_channel:
                for text_channel in guild.text_channels:
                    perms = text_channel.permissions_for(guild.me)
                    if perms.send_messages and perms.embed_links:
                        dest_channel = text_channel
                        break
            
            if dest_channel:
                await dest_channel.send(msg_final)

        except Exception as e:
            print(f"Error notificando nivel de voz: {e}")

async def setup(bot):
    await bot.add_cog(VoiceXP(bot))