import logging
import discord
import datetime
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
        self.persistence_scheduler.start()

    def cog_unload(self):
        self.node_monitor.cancel()
        self.persistence_scheduler.cancel()

    @tasks.loop(minutes=1)
    async def node_monitor(self):
        """Monitoreo de salud de nodos movido a eventos."""
        if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
            music_cog = self.bot.get_cog("Music")
            if music_cog:
                logger.warning("⚠️ [Music Event] Nodos caídos. Solicitando reconexión al Cog...")
                await music_cog.connect_best_node(max_retries=1)

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
        if not player or not hasattr(player, "home"): return

        await db_service.record_song_feedback(player.guild.id, payload.track.identifier, is_skip=False)
        
        lang = await lang_service.get_guild_lang(player.guild.id)
        embed = music_service.create_np_embed(player, payload.track, lang)
        view = music_service.MusicControls(player, lang=lang)
        
        # Limpieza de mensajes anteriores
        if hasattr(player, "last_msg") and player.last_msg:
            try: await player.last_msg.delete()
            except: pass

        # --- MEJORA DE RICH PRESENCE ---
        # Calculamos el tiempo de finalización para la barra de progreso en el perfil
        start_time = datetime.datetime.now(datetime.timezone.utc)
        end_time = None
        if not payload.track.is_stream:
            end_time = start_time + datetime.timedelta(milliseconds=payload.track.length)

        album_obj = getattr(payload.track, "album", None)
        album_name = getattr(album_obj, "name", "Single") if album_obj else "Single"

        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{payload.track.title}",
            details=f"👤 {payload.track.author}",
            state=f"💿 {album_name} | 🔊 {player.volume}%",
            start=start_time,
            end=end_time,
            assets={
                'large_image': settings.CONFIG["bot_config"]["presence_asset"],
                'large_text': settings.CONFIG["bot_config"]["description"]
            }
        )
        await self.bot.change_presence(activity=activity)

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
            # Al terminar la música, podemos volver al estado rotativo normal
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name=f"{settings.CONFIG['bot_config']['prefix']}help",
                assets={'large_image': settings.CONFIG["bot_config"]["presence_asset"]}
            )
            await self.bot.change_presence(activity=activity)
            await music_service.cleanup_player(self.bot, player)
            if player.connected: await player.disconnect()

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        logger.error(f"❌ [Music Event] Error en {payload.track.title}: {payload.exception}", exc_info=payload.exception)
        player = payload.player
        if not player: return

        current_position = int(player.position)
        
        # Sistema de Fallback en cadena: Spotify -> YouTube -> SoundCloud
        err_msg = str(payload.exception)
        is_yt_error = "No supported audio streams" in err_msg or "403" in err_msg or "not available" in err_msg
        uri = (payload.track.uri or "").lower()

        # Si falla algo que no es SoundCloud, intentamos el último recurso (SC)
        if is_yt_error:
            # Si falló Spotify (que suele resolver a YT) o YouTube directamente, saltamos a SoundCloud
            if "spotify" in uri or "youtube" in uri or "youtu.be" in uri:
                logger.info(f"🔄 [Music Event] Intentando fallback a SoundCloud para: {payload.track.title}")
                try:
                    query = f"scsearch:{payload.track.title} {payload.track.author}"
                    tracks = await wavelink.Playable.search(query)
                    if tracks:
                        fallback_track = tracks[0]
                        if hasattr(payload.track, "requester"):
                            fallback_track.requester = payload.track.requester
                        
                        await player.play(fallback_track, start=current_position)
                        return
                except Exception:
                    logger.exception("❌ Fallback fallido")

        player.last_track_error = True
        await player.stop()

async def setup(bot):
    await bot.add_cog(MusicEvents(bot))