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

    @tasks.loop(seconds=settings.VOICE_XP_INTERVAL)
    async def voice_xp_loop(self):
        """
        Tarea periódica que otorga XP a usuarios en canales de voz.
        Se ejecuta cada X segundos definidos en settings.py.
        """
        # Esperar a que el bot esté listo
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            # Iterar canales de voz del servidor
            for channel in guild.voice_channels:
                # REGLA 1: Ignorar canal si está vacío o solo hay 1 persona
                if len(channel.members) < 2:
                    continue
                
                # REGLA 2: Ignorar canal AFK del servidor (si está configurado)
                if guild.afk_channel and channel.id == guild.afk_channel.id:
                    continue

                for member in channel.members:
                    # REGLA 3: Ignorar bots
                    if member.bot:
                        continue
                    
                    # REGLA 4: Ignorar muteados/ensordecidos (Anti-Farm)
                    # self_mute/deaf = El usuario se muteó a sí mismo
                    # mute/deaf = Un admin lo muteó (opcional: quitar si quieres dar XP a muteados por admin)
                    if member.voice.self_mute or member.voice.self_deaf or member.voice.deaf:
                        continue

                    # ✅ SI PASA TODOS LOS FILTROS: DAR XP
                    try:
                        # Usamos la función optimizada de db_service (con caché)
                        nuevo_nivel, subio = await db_service.add_xp(guild.id, member.id, settings.VOICE_XP_AMOUNT)
                        
                        if subio:
                            await self._notificar_nivel(guild, channel, member, nuevo_nivel)
                            
                    except Exception as e:
                        print(f"Error VoiceXP en {guild.name}: {e}")

    async def _notificar_nivel(self, guild, channel, member, nuevo_nivel):
        """Envía el mensaje de Level Up al chat de texto asociado al canal de voz o al default."""
        try:
            lang = await lang_service.get_guild_lang(guild.id)
            
            # Buscar configuración personalizada
            config = await db_service.get_guild_config(guild.id)
            user_data = await db_service.fetch_one("SELECT personal_level_msg FROM users WHERE user_id = ?", (member.id,))
            
            # Prioridad de mensaje: Usuario > Servidor > Default
            if user_data and user_data['personal_level_msg']:
                msg_raw = user_data['personal_level_msg']
            elif config.get('server_level_msg'):
                msg_raw = config['server_level_msg']
            else:
                msg_raw = lang_service.get_text("level_up_default", lang)
            
            msg_final = msg_raw.replace("{user}", member.mention)\
                               .replace("{level}", str(nuevo_nivel))\
                               .replace("{server}", guild.name)

            # Intentar enviar al chat del sistema (logs) o al primer canal de texto visible
            dest_channel = None
            if config.get('logs_channel_id'):
                dest_channel = guild.get_channel(config['logs_channel_id'])
            
            # Si no hay logs, intentamos un canal "general"
            if not dest_channel:
                for text_channel in guild.text_channels:
                    if text_channel.permissions_for(guild.me).send_messages:
                        dest_channel = text_channel
                        break
            
            if dest_channel:
                await dest_channel.send(msg_final)

        except Exception as e:
            print(f"Error notificando nivel de voz: {e}")

async def setup(bot):
    await bot.add_cog(VoiceXP(bot))