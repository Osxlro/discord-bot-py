import discord
from discord.ext import commands, tasks
import logging
from services.features import stream_alert_service
from services.core import lang_service
from services.utils import embed_service

logger = logging.getLogger(__name__)

class StreamAlertsTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.youtube_check_loop.start()

    def cog_unload(self):
        self.youtube_check_loop.cancel()

    @tasks.loop(minutes=5.0)
    async def youtube_check_loop(self):
        """Loop periódico para verificar nuevos vídeos de YouTube en canales configurados."""
        try:
            logger.debug("Bucle de alertas de YouTube: Iniciando comprobación...")
            alerts = await stream_alert_service.get_all_stream_alerts()
            if not alerts:
                return

            # Agrupar alertas por canal de YouTube para consultar cada feed una sola vez
            unique_channels = set(alert["channel_name"] for alert in alerts if alert["platform"] == "youtube")
            
            import asyncio
            sem = asyncio.Semaphore(5)
            
            async def safe_check(channel_id):
                async with sem:
                    return channel_id, await stream_alert_service.check_youtube_feed(channel_id)
            
            tasks = [safe_check(c) for c in unique_channels]
            results = await asyncio.gather(*tasks)
            feeds = {cid: data for cid, data in results if data}

            # Procesar las alertas de cada servidor
            for alert in alerts:
                if alert["platform"] != "youtube":
                    continue
                
                channel_name = alert["channel_name"]
                guild_id = alert["guild_id"]
                last_status = alert["last_status"]
                discord_channel_id = alert["discord_channel_id"]
                role_id = alert["role_id"]

                # Si no pudimos obtener el feed, omitir
                if channel_name not in feeds:
                    continue

                feed = feeds[channel_name]
                video_id = feed["video_id"]
                video_title = feed["title"]
                author = feed["author"]
                video_link = feed["link"]

                # Caso 1: Primera vez que se registra el canal (last_status es NULL)
                # Inicializamos el ID del último vídeo para no notificar vídeos antiguos.
                if last_status is None:
                    await stream_alert_service.update_stream_status(guild_id, "youtube", channel_name, video_id)
                    logger.info(f"Inicializado estado de YouTube para canal {channel_name} en guild {guild_id} con video {video_id}")
                    continue

                # Caso 2: Se detecta un vídeo nuevo
                if video_id != last_status:
                    # Actualizamos el estado primero para evitar notificaciones duplicadas en caso de fallo posterior
                    await stream_alert_service.update_stream_status(guild_id, "youtube", channel_name, video_id)
                    
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue

                    channel = guild.get_channel(discord_channel_id)
                    if not channel:
                        continue

                    # Obtener el idioma configurado
                    lang = await lang_service.get_guild_lang(guild_id)

                    # Construir la mención del rol si está configurado
                    mention_str = ""
                    if role_id:
                        role = guild.get_role(role_id)
                        if role:
                            mention_str = role.mention

                    # Reemplazar la mención y el embed con el mensaje personalizado si existe.
                    # Si no hay mensaje personalizado, solo pon el video y ya (más la mención si hay).
                    custom_msg = alert.get("custom_message")
                    if custom_msg:
                        content = custom_msg.replace("{role}", mention_str).replace("{author}", author).replace("{title}", video_title).replace("{link}", video_link)
                        if "{link}" not in custom_msg:
                            content += f"\n{video_link}"
                    else:
                        if mention_str:
                            content = f"{mention_str} {video_link}"
                        else:
                            content = video_link
                    
                    try:
                        await channel.send(content=content)
                        logger.info(f"Notificación enviada para {author} en guild {guild_id}, canal {discord_channel_id}")
                    except discord.Forbidden:
                        logger.warning(f"No hay permisos para enviar mensajes en el canal {discord_channel_id} del guild {guild_id}")
                    except Exception as e:
                        logger.exception(f"Error enviando notificación de YouTube: {e}")

        except Exception as e:
            logger.exception(f"Error general en bucle de alertas de YouTube: {e}")

    @youtube_check_loop.before_loop
    async def before_youtube_check_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(StreamAlertsTask(bot))
