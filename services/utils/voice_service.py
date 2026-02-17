import logging
import asyncio
import discord
from config import settings
from ui import voice_ui

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
    except Exception:
        logger.exception(f"Error en join_voice service ({guild.name})")
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
        except Exception:
            logger.exception(f"❌ [Voice Service] Fallo reconexión ({i+1})")
    
    voice_targets.pop(guild.id, None)

async def handle_join(guild: discord.Guild, member: discord.Member, lang: str):
    """Orquesta la lógica para unirse a un canal de voz."""
    if not member.voice:
        return None, voice_ui.get_voice_error_embed(lang, "voice_error_user")

    channel = member.voice.channel
    permissions = channel.permissions_for(guild.me)
    if not permissions.connect:
        return None, voice_ui.get_voice_error_embed(lang, "voice_error_perms")

    if await join_voice(guild, channel):
        return voice_ui.get_join_success_embed(lang, channel.name), None
    
    return None, voice_ui.get_voice_error_embed(lang, "error_generic")

async def handle_leave(guild: discord.Guild, lang: str):
    """Orquesta la lógica para salir de un canal de voz."""
    if await leave_voice(guild):
        return voice_ui.get_leave_success_embed(lang), None
    return None, None

async def handle_voice_state_update(bot, member, before, after):
    """Procesa cambios en el estado de voz del bot."""
    if member.id != bot.user.id:
        return

    if before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
        if member.guild.id in voice_targets:
            voice_targets[member.guild.id] = after.channel.id
            logger.info(f"🔄 [Voice] Bot movido manualmente a {after.channel.name} en {member.guild.name}. Objetivo actualizado.")

    elif before.channel is not None and after.channel is None:
        target_channel_id = voice_targets.get(member.guild.id)
        if target_channel_id and target_channel_id == before.channel.id:
            logger.warning(f"⚠️ [Voice] Desconexión inesperada en {member.guild.name}. Iniciando reconexión...")
            bot.loop.create_task(reconnect_voice(bot, member.guild, target_channel_id))
