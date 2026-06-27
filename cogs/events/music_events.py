import logging
import discord
import wavelink
import asyncio
from discord.ext import commands, tasks
from services.features import music_service, voice_chill_service, music_algorithm_service

logger = logging.getLogger(__name__)

class MusicEvents(commands.Cog):
    """Maneja el ciclo de vida de Lavalink y eventos de reproducción."""
    def __init__(self, bot):
        self.bot = bot
        self.recommender = music_algorithm_service.RecommendationEngine()
        self.node_monitor.start()
        self.persistence_scheduler.start()

    def cog_unload(self):
        self.node_monitor.cancel()
        self.persistence_scheduler.cancel()
        # Cerrar sesión del recomendador
        if hasattr(self.recommender, "close"):
            asyncio.create_task(self.recommender.close())

    def _recover_player(self, payload) -> wavelink.Player | None:
        """Intenta recuperar el wavelink.Player de la lista de voice_clients si el payload tiene player = None."""
        player = payload.player
        if player:
            return player
        
        track = getattr(payload, 'track', None)
        if track and hasattr(track, 'uri') and track.uri:
            for voice_client in self.bot.voice_clients:
                if isinstance(voice_client, wavelink.Player):
                    if voice_client.current and voice_client.current.uri == track.uri:
                        logger.info(f"🔍 [Music Event] Player recuperado por pista actual en guild {voice_client.guild.id}")
                        return voice_client
        return None

    @tasks.loop(minutes=1)
    async def node_monitor(self):
        """Monitoreo de salud de nodos movido a eventos."""
        if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
            await music_service.connect_nodes(self.bot)

    @node_monitor.before_loop
    async def before_node_monitor(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=60)
    async def persistence_scheduler(self):
        """Guarda periódicamente el estado de todos los reproductores activos."""
        for node in wavelink.Pool.nodes.values():
            for player in node.players.values():
                if player.playing:
                    await music_service.save_player_state(player)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"✅ [Music Event] Nodo listo: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        try:
            player = self._recover_player(payload)
            logger.info(f"🎶 [Music Event] on_wavelink_track_start disparado: {payload.track.title}")
            if not player: return
            
            home = getattr(player, "home", None) or music_service.get_player_home(player.guild.id)
            if not home:
                logger.warning(f"⚠️ [Music Event] No se encontró canal de texto (home) para el servidor {player.guild.id}")
                return

            # Lógica de mensaje NP delegada al servicio
            await music_service.send_now_playing(self.bot, player, payload.track)
        except Exception as e:
            logger.exception(f"🔥 [Music Event] Error en on_wavelink_track_start: {e}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = self._recover_player(payload)
        reason_str = payload.reason if hasattr(payload, 'reason') else 'N/A'
        logger.debug(f"🛑 [Music Event] on_wavelink_track_end disparado para: {payload.track.title} | Razón: {reason_str}")
        
        # Lógica de Autoplay / Siguiente canción
        if payload.reason == "replaced": return

        if payload.reason == "loadFailed":
            if player:
                logger.info(f"🔄 [Music Event] loadFailed detectado para '{payload.track.title}'. Intentando fallback...")
                success = await music_service.handle_track_fallback(player, payload.track)
                if success:
                    return
                logger.warning("❌ [Music Event] Fallback fallido tras loadFailed. Saltando a la siguiente...")
            else:
                logger.warning("⚠️ [Music Event] loadFailed detectado pero no se pudo recuperar el Player.")
                return

        if not player: return
        if player.autoplay == wavelink.AutoPlayMode.enabled: return

        # 1. Bucle de Pista (Single Track Loop)
        if player.queue.mode == wavelink.QueueMode.loop:
            logger.debug("🔁 [Music Event] Modo Bucle Pista activo. Repitiendo...")
            return await player.play(payload.track)

        # 2. Siguiente canción (Normal o Loop All)
        if not player.queue.is_empty:
            next_track = player.queue.get()
            logger.debug(f"⏭️ [Music Event] Siguiente pista de la cola: {next_track.title}")
            await player.play(next_track)
            
        elif getattr(player, "smart_autoplay", False):
            logger.debug("🧠 [Music Event] Cola vacía. Generando recomendación Smart Autoplay...")
            # El algoritmo decide la siguiente canción basándose en metadatos
            rec = await self.recommender.get_recommendation(player)
            if rec: await player.play(rec)
        else:
            logger.debug("🧹 [Music Event] Cola vacía y Autoplay inactivo. Limpiando player...")
            # Limpieza total al terminar la sesión
            await music_service.cleanup_player(player)
            await music_service.reset_presence(self.bot)
            if player.connected: await player.disconnect()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Detecta desconexiones manuales para limpiar la interfaz, o si el canal se queda vacío."""
        # Caso 1: El bot mismo es desconectado del canal
        if member.id == self.bot.user.id:
            if before.channel and not after.channel:
                player: wavelink.Player = member.guild.voice_client
                if player:
                    # Esperar un momento para verificar si es una reconexión automática temporal
                    await asyncio.sleep(2.5)
                    # Si el bot se ha reconectado y sigue conectado, no limpiamos el reproductor
                    if player.connected:
                        logger.info(f"🔄 [Music Event] Reconexión automática detectada en {member.guild.name}. Conservando reproductor.")
                        return
                    
                    logger.info(f"🔌 [Music Event] Desconexión definitiva detectada en {member.guild.name}. Limpiando UI...")
                    await music_service.cleanup_player(player)
            return

        # Caso 2: Otro miembro cambia de estado de voz
        guild = member.guild
        player = guild.voice_client

        # Si el bot está en un canal y el miembro se desconectó o cambió de canal desde nuestro canal de voz
        if player and player.channel and before.channel and before.channel.id == player.channel.id:
            # Si el canal quedó sin humanos (solo bots o vacío)
            # Excluimos el modo AFK intencional (voice_targets)
            if guild.id not in voice_chill_service.voice_targets:
                human_members = [m for m in player.channel.members if not m.bot]
                if not human_members:
                    logger.info(f"🔌 [Music Event] Canal vacío detectado en {guild.name} (se fue el último miembro). Desconectando...")
                    await music_service.cleanup_player(player)
                    await player.disconnect()

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        logger.error(f"❌ [Music Event] Error en {payload.track.title}: {payload.exception}", exc_info=payload.exception)
        player = self._recover_player(payload)
        if not player:
            logger.warning("⚠️ [Music Event] No se pudo recuperar el Player para procesar la excepción.")
            return

        # Intentar recuperar la reproducción con una fuente alternativa
        success = await music_service.handle_track_fallback(player, payload.track)
        if success:
            return

        # Si no hay fallback posible, limpiar y detener
        player.last_track_error = True
        await music_service.cleanup_player(player)
        await player.stop()

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload):
        """Maneja el bug de canciones que se quedan reproduciendo infinitamente sin audio."""
        logger.warning(f"⚠️ [Music Event] Pista atascada detectada: {payload.track.title}. Forzando salto...")
        # Al saltar, se disparará on_track_end y la cola seguirá su curso normal
        player = self._recover_player(payload)
        if player:
            await player.skip(force=True)

async def setup(bot):
    await bot.add_cog(MusicEvents(bot))