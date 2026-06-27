import logging
import discord

logger = logging.getLogger(__name__)

async def connect_channel(channel: discord.VoiceChannel, self_deaf: bool = True, self_mute: bool = True) -> bool:
    """Helper básico para conectar o mover al bot a un canal de voz."""
    try:
        guild = channel.guild
        if guild.voice_client:
            await guild.voice_client.move_to(channel)
            # Aseguramos que siga en los modos deseados al moverse
            if guild.me.voice:
                try:
                    await guild.me.edit(deafen=self_deaf, mute=self_mute)
                except Exception:
                    pass
        else:
            await channel.connect(self_deaf=self_deaf, self_mute=self_mute)
        return True
    except Exception:
        logger.exception(f"Error al conectar al canal de voz {channel.id} en {guild.name}")
        return False

async def disconnect_channel(guild: discord.Guild) -> bool:
    """Helper básico para desconectar al bot del canal de voz."""
    if guild.voice_client:
        await guild.voice_client.disconnect()
        return True
    return False
