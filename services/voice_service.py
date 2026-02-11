import logging
import asyncio
import discord
from config import settings

logger = logging.getLogger(__name__)

# Persistencia de dónde debería estar el bot (guild_id: channel_id)
voice_targets = {}

async def join_voice(guild: discord.Guild, channel: discord.VoiceChannel) -> bool:
    """Conecta o mueve al bot a un canal de voz en modo Chill (Sordo/Mute)."""
    try:
        if guild.voice_client:
            await guild.voice_client.move_to(channel)
            # Aseguramos que siga en modo "Chill" al moverse
            if guild.me.voice:
                try: await guild.me.edit(deafen=True, mute=True)
                except: pass
        else:
            await channel.connect(self_deaf=True, self_mute=True)
        
        voice_targets[guild.id] = channel.id
        return True
    except Exception as e:
        logger.error(f"Error en join_voice service ({guild.name}): {e}")
        return False

async def leave_voice(guild: discord.Guild) -> bool:
    """Desconecta al bot y elimina el objetivo de persistencia."""
    if guild.voice_client:
        voice_targets.pop(guild.id, None)
        await guild.voice_client.disconnect()
        return True
    return False

async def reconnect_voice(bot, guild: discord.Guild, channel_id: int):
    """Intenta reconectar al canal de voz con backoff exponencial."""
    channel = guild.get_channel(channel_id)
    if not channel: return

    backoff = settings.VOICE_CONFIG.get("RECONNECT_BACKOFF", [5, 10, 30])
    
    for i, wait in enumerate(backoff):
        await asyncio.sleep(wait)
        try:
            vc = guild.voice_client
            is_connected = False
            
            if vc:
                if hasattr(vc, 'connected'): is_connected = vc.connected
                elif hasattr(vc, 'is_connected'): is_connected = vc.is_connected()
            
            if is_connected: return 
            
            logger.info(f"🔄 [Voice Service] Intento de reconexión {i+1}/{len(backoff)} en {guild.name}...")
            
            if vc:
                try: await vc.disconnect(force=True)
                except: pass

            await channel.connect(self_deaf=True, self_mute=True)
            logger.info(f"✅ [Voice Service] Reconexión exitosa en {guild.name}.")
            return
        except Exception as e:
            logger.error(f"❌ [Voice Service] Fallo reconexión ({i+1}): {e}")
    
    voice_targets.pop(guild.id, None)
