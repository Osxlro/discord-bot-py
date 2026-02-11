import logging
import discord
import wavelink
import asyncio
from discord.ext import commands, tasks
from services import music_service, lang_service, embed_service, algorithm_service, db_service
from config import settings

logger = logging.getLogger(__name__)

class MusicEvents(commands.Cog):
    """Maneja el ciclo de vida de Lavalink y eventos de reproducción."""
    def __init__(self, bot):
        self.bot = bot
        self.recommender = algorithm_service.RecommendationEngine()
        self.node_monitor.start()

    def cog_unload(self):
        self.node_monitor.cancel()

    @tasks.loop(minutes=1)
    async def node_monitor(self):
        """Monitoreo de salud de nodos movido a eventos."""
        if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
            music_cog = self.bot.get_cog("Music")
            if music_cog:
                logger.warning("⚠️ [Music Event] Nodos caídos. Solicitando reconexión al Cog...")
                await music_cog.connect_best_node(max_retries=1)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"✅ [Music Event] Nodo listo: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        if not player or not hasattr(player, "home"): return

        await db_service.record_song_feedback(player.guild.id, payload.track.identifier, is_skip=False)
        
        lang = await lang_service.get_guild_lang(player.guild.id)
        embed = music_service.create_np_embed(player, payload.track, lang)
        view = music_service.MusicControls(player, lang=lang)
        
        # Limpieza de mensajes anteriores
        if hasattr(player, "last_msg") and player.last_msg:
            try: await player.last_msg.delete()
            except: pass

        player.last_msg = await player.home.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player: return

        # Lógica de Autoplay / Siguiente canción
        if payload.reason == "replaced": return
        if player.autoplay == wavelink.AutoPlayMode.enabled: return

        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
        elif getattr(player, "smart_autoplay", False):
            rec = await self.recommender.get_recommendation(player)
            if rec: await player.play(rec)
        else:
            await music_service.cleanup_player(self.bot, player)
            if player.connected: await player.disconnect()

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        logger.error(f"❌ [Music Event] Error en {payload.track.title}: {payload.exception}")
        player = payload.player
        
        # Fallback a SoundCloud si es error de YouTube
        err_msg = str(payload.exception)
        if "No supported audio streams" in err_msg and "youtube" in (payload.track.uri or ""):
            query = f"scsearch:{payload.track.title} {payload.track.author}"
            tracks = await wavelink.Playable.search(query)
            if tracks:
                await player.play(tracks[0])
                return

        await player.stop()

async def setup(bot):
    await bot.add_cog(MusicEvents(bot))