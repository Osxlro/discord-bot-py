import logging
import discord
import wavelink
import asyncio
from discord.ext import commands, tasks
from services.features import music_service
from services.utils import algorithm_service

logger = logging.getLogger(__name__)

class MusicEvents(commands.Cog):

    """Maneja el ciclo de vida de Lavalink y eventos de reproducción."""
    def __init__(self, bot):
        self.bot = bot
        self.recommender = algorithm_service.RecommendationEngine()
        self.node_monitor.start()
        self.persistence_scheduler.start()

    def cog_unload(self):
        self.node_monitor.cancel()
        self.persistence_scheduler.cancel()
        # Cerrar sesión del recomendador
        if hasattr(self.recommender, "close"):
            asyncio.create_task(self.recommender.close())

    @tasks.loop(minutes=1)
    async def node_monitor(self):
        """Monitoreo de salud de nodos movido a eventos."""
        if not self.bot.is_ready():
            return
        await self.bot.wait_until_ready()
        
        if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
            await music_service.connect_nodes(self.bot)

    @tasks.loop(seconds=20)
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
        player = payload.player
        logger.debug(f"🎶 [Music Event] on_wavelink_track_start disparado: {payload.track.title}")
        if not player or not hasattr(player, "home"): return

        # Lógica de mensaje NP delegada al servicio
        await music_service.send_now_playing(self.bot, player, payload.track)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        reason_str = payload.reason if hasattr(payload, 'reason') else 'N/A'
        logger.debug(f"🛑 [Music Event] on_wavelink_track_end disparado para: {payload.track.title} | Razón: {reason_str}")
        if not player: return

        # Lógica de Autoplay / Siguiente canción
        if payload.reason in ("replaced", "loadFailed"): return
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
        """Detecta desconexiones manuales para limpiar la interfaz."""
        if member.id != self.bot.user.id: return

        # Si el bot fue desconectado del canal
        if before.channel and not after.channel:
            player: wavelink.Player = member.guild.voice_client
            if player:
                logger.info(f"🔌 [Music Event] Desconexión detectada en {member.guild.name}. Limpiando UI...")
                await music_service.cleanup_player(player)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        logger.error(f"❌ [Music Event] Error en {payload.track.title}: {payload.exception}", exc_info=payload.exception)
        player = payload.player
        if not player: return

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
        player = payload.player
        if player:
            await player.skip(force=True)

async def setup(bot):
    await bot.add_cog(MusicEvents(bot))