import logging
import asyncio
import wavelink
from discord.ext import commands
from services import embed_service, lang_service
from config import settings

logger = logging.getLogger(__name__)

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_targets = {} # {guild_id: channel_id} - Dónde debería estar el bot

    def cog_unload(self):
        """Limpia las conexiones de voz al descargar el cog."""
        for guild_id in list(self.voice_targets.keys()):
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client:
                self.bot.loop.create_task(guild.voice_client.disconnect(force=True))
        self.voice_targets.clear()

    @commands.hybrid_command(name="join", description="Conecta el bot a tu canal de voz (Modo Chill).")
    async def join(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # 1. Verificar si el usuario tiene canal
        if not ctx.author.voice:
            msg = lang_service.get_text("voice_error_user", lang)
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg))

        channel = ctx.author.voice.channel

        # 2. Verificar permisos del bot
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.connect:
            msg = lang_service.get_text("voice_error_perms", lang)
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg))

        # 3. Conectar (u mover si ya está en otro)
        try:
            if ctx.voice_client:
                # Si el cliente NO es un Player de Wavelink (ej. conexión antigua), reconectamos
                if not isinstance(ctx.voice_client, wavelink.Player):
                    await ctx.voice_client.disconnect(force=True)
                    await channel.connect(cls=wavelink.Player, self_deaf=True, self_mute=True)
                
                # Si el cliente está en un estado inconsistente, forzamos desconexión primero
                elif not ctx.voice_client.connected:
                    await ctx.voice_client.disconnect(force=True)
                    await channel.connect(cls=wavelink.Player, self_deaf=True, self_mute=True)
                else:
                    await ctx.voice_client.move_to(channel)
                    # Aseguramos que siga en modo "Chill" (Sordo/Mute) al moverse
                    try: 
                        if ctx.guild.me.voice: await ctx.guild.me.edit(deafen=True, mute=True)
                    except: pass
            else:
                await channel.connect(cls=wavelink.Player, self_deaf=True, self_mute=True)
            
            self.voice_targets[ctx.guild.id] = channel.id
            msg = lang_service.get_text("voice_join", lang, channel=channel.name)
            await ctx.send(embed=embed_service.success(lang_service.get_text("voice_title", lang), msg, lite=True))
            logger.info(f"Voice Join: {ctx.guild.name} -> {channel.name}")
            
        except Exception as e:
            logger.error(f"Error Voice Join en {ctx.guild.name}: {e}")
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), f"{e}"))

    @commands.hybrid_command(name="leave", description="Desconecta al bot del canal de voz.")
    async def leave(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if ctx.voice_client:
            # Eliminamos la persistencia porque el usuario pidió salir
            self.voice_targets.pop(ctx.guild.id, None)
                
            await ctx.voice_client.disconnect()
            msg = lang_service.get_text("voice_leave", lang)
            await ctx.send(embed=embed_service.success(lang_service.get_text("voice_title", lang), msg, lite=True))
            logger.info(f"Voice Leave: {ctx.guild.name}")
        else:
            # Si no está conectado, reacciona con un emoji simple
            try: await ctx.message.add_reaction("❓")
            except: pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Detecta desconexiones forzadas o inesperadas."""
        # Si el bot es el que cambió de estado
        if member.id == self.bot.user.id:
            # 1. Movimiento manual (o por comando) a otro canal
            if before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
                if member.guild.id in self.voice_targets:
                    self.voice_targets[member.guild.id] = after.channel.id
                    logger.info(f"🔄 [Voice] Bot movido manualmente a {after.channel.name} en {member.guild.name}. Objetivo actualizado.")

            # 2. Desconexión inesperada
            elif before.channel is not None and after.channel is None:
                target_channel_id = self.voice_targets.get(member.guild.id)
                
                # Si tenemos un objetivo guardado, intentamos reconectar
                if target_channel_id and target_channel_id == before.channel.id:
                    logger.warning(f"⚠️ [Voice] Desconexión inesperada en {member.guild.name}. Iniciando reconexión...")
                    self.bot.loop.create_task(self._reconnect_voice(member.guild, target_channel_id))

    async def _reconnect_voice(self, guild, channel_id):
        """Intenta reconectar al canal de voz con backoff exponencial."""
        channel = guild.get_channel(channel_id)
        if not channel: return

        backoff = settings.VOICE_CONFIG["RECONNECT_BACKOFF"]
        
        for i, wait in enumerate(backoff):
            await asyncio.sleep(wait)
            try:
                if guild.voice_client and guild.voice_client.connected:
                    return # Ya se reconectó
                
                logger.info(f"🔄 [Voice] Intento de reconexión {i+1}/{len(backoff)} en {guild.name}...")
                await channel.connect(cls=wavelink.Player, self_deaf=True, self_mute=True)
                logger.info(f"✅ [Voice] Reconexión exitosa en {guild.name}.")
                return
            except Exception as e:
                logger.error(f"❌ [Voice] Fallo reconexión ({i+1}): {e}")
        
        # Si falla todo, limpiamos el target
        self.voice_targets.pop(guild.id, None)

async def setup(bot):
    await bot.add_cog(Voice(bot))