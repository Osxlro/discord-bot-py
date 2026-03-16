import discord
import asyncio
import wavelink
import logging
import re
import datetime
from discord import app_commands
from config import settings
from services.utils import embed_service
from services.core import lang_service, persistence_service
from services.utils import voice_service
from ui.music_ui import MusicControls, create_np_embed, format_duration, get_source_icon, get_source_color

logger = logging.getLogger(__name__)

_is_connecting = False

# =============================================================================
# 0. CONFIGURACIÓN DE FILTROS (PRESETS)
# =============================================================================
FILTERS_CONFIG = {
    "bassboost": {"type": "equalizer", "bands": [(0, 0.3), (1, 0.25), (2, 0.2), (3, 0.1), (4, 0.05)]},
    "superbass": {"type": "equalizer", "bands": [(0, 0.5), (1, 0.4), (2, 0.3), (3, 0.2), (4, 0.1)]},
    "hifi":      {"type": "equalizer", "bands": [(0, 0.15), (1, 0.1), (2, 0.05), (12, 0.05), (13, 0.1), (14, 0.15)]},
    "surround":  {"type": "rotation", "rotation_hz": 0.02},
    "metal":     {"type": "equalizer", "bands": [(0, 0.3), (1, 0.2), (2, 0.1), (3, -0.1), (4, -0.2), (5, -0.1), (6, 0.0), (7, 0.1), (8, 0.2), (9, 0.3), (10, 0.35), (11, 0.4), (12, 0.4), (13, 0.4), (14, 0.4)]},
    "pop":       {"type": "equalizer", "bands": [(0, -0.05), (1, 0.1), (2, 0.2), (3, 0.15), (4, 0.05)]},
    "soft":      {"type": "lowpass", "smoothing": 20.0},
    "treble":    {"type": "equalizer", "bands": [(10, 0.1), (11, 0.2), (12, 0.25), (13, 0.3)]},
    "nightcore": {"type": "timescale", "speed": 1.25, "pitch": 1.25},
    "vaporwave": {"type": "timescale", "speed": 0.85, "pitch": 0.8},
    "8d":        {"type": "rotation", "rotation_hz": 0.2},
    "karaoke":   {"type": "karaoke"},
    "tremolo":   {"type": "tremolo", "frequency": 2.0, "depth": 0.5},
    "vibrato":   {"type": "vibrato", "frequency": 2.0, "depth": 0.5},
    "flat":      {"type": "clear"}
}

# =============================================================================
# 1. UTILIDADES DE FORMATEO Y TEXTO
# =============================================================================

def clean_track_title(title: str) -> str:
    """Limpia metadatos innecesarios de los títulos para mejorar la precisión de búsqueda."""
    if not title: return ""
    title = re.sub(r"[\(\[].*?[\)\]]", "", title)
    noise = ["official video", "official audio", "lyrics", "hd", "4k", "video oficial", "letra", "full hd", "audio"]
    for n in noise:
        title = re.compile(re.escape(n), re.IGNORECASE).sub("", title)
    return title.strip()

# =============================================================================
# 2. GESTIÓN DE PRESENCIA Y ESTADO
# =============================================================================

async def update_presence(bot: discord.Client, player: wavelink.Player, track: wavelink.Playable, lang: str):
    """Actualiza el Rich Presence del bot basado en la canción actual."""
    start_time = datetime.datetime.now(datetime.timezone.utc)
    end_time = None
    if not track.is_stream:
        end_time = start_time + datetime.timedelta(milliseconds=track.length)

    single_label = lang_service.get_text("music_album_single", lang)
    album_obj = getattr(track, "album", None)
    album_name = getattr(album_obj, "name", single_label) if album_obj else single_label

    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name=f"{track.title}",
        details=f"💿 {album_name}",
        state=f"👤 {track.author} | 🔊 {player.volume}%",
        start=start_time,
        end=end_time,
        assets={
            'large_image': settings.CONFIG["bot_config"]["presence_asset"],
            'large_text': settings.CONFIG["bot_config"]["description"]
        }
    )
    await bot.change_presence(activity=activity)

async def reset_presence(bot: discord.Client):
    """Restaura el estado normal del bot al detener la música."""
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name=f"{settings.CONFIG['bot_config']['prefix']}help",
        assets={'large_image': settings.CONFIG["bot_config"]["presence_asset"]}
    )
    await bot.change_presence(activity=activity)

# =============================================================================
# 3. LÓGICA DE INTERFAZ (VISTAS Y BOTONES)
# =============================================================================

# =============================================================================
# 4. NÚCLEO DEL REPRODUCTOR Y BÚSQUEDA
# =============================================================================

async def cleanup_player(player: wavelink.Player, skip_message_edit: bool = False):
    """Realiza limpieza de interfaz y persistencia al detener el player."""
    if not player: return

    # 1. Limpiar persistencia de Voice
    voice_service.voice_targets.pop(player.guild.id, None)

    # 2. Manejar mensaje y vista
    msg = getattr(player, "last_msg", None)
    view = getattr(player, "last_view", None)
    
    if view:
        for child in view.children:
            child.disabled = True
        view.stop()

    if msg:
        try:
            if skip_message_edit:
                await msg.delete()
            else:
                await msg.edit(view=view)
        except (discord.HTTPException, discord.Forbidden): pass

    # Las siguientes operaciones solo son válidas para wavelink.Player
    if isinstance(player, wavelink.Player):
        # Limpiar referencias
        player.last_msg = None
        player.last_view = None
        player.home = None # Liberar referencia al canal de texto
        
        # Limpiar cola
        if hasattr(player, "queue"):
            try: player.queue.clear()
            except: pass
            
        # Resetear estados internos
        player.smart_autoplay = False
        player.last_track_error = False
        await player.set_filters(wavelink.Filters()) # Limpiar filtros

async def ensure_player(ctx, lang: str) -> wavelink.Player | None:
    """Asegura que el bot esté conectado correctamente y retorna el player."""
    logger.debug("🎵 [Music Service] Ejecutando ensure_player")
    if not ctx.author.voice:
        logger.debug("🎵 [Music Service] Usuario no está en canal de voz.")
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_join", lang)))
        return None

    permissions = ctx.author.voice.channel.permissions_for(ctx.guild.me)
    if not permissions.connect or not permissions.speak:
        logger.debug("🎵 [Music Service] Permisos insuficientes para el canal de voz.")
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("voice_error_perms", lang)))
        return None

    try:
        # Aislar completamente el reproductor de música del voice_service
        # para que no sabotee la conexión enviando desconexiones fantasma.
        if ctx.guild.id in voice_service.voice_targets:
            voice_service.voice_targets.pop(ctx.guild.id)

        if ctx.voice_client and not isinstance(ctx.voice_client, wavelink.Player):
            logger.debug("🎵 [Music Service] Reemplazando VoiceClient estándar por wavelink.Player...")
            await ctx.voice_client.disconnect(force=True)
            # CRÍTICO: Esperar a que el Gateway de Discord procese la desconexión
            await asyncio.sleep(1.5)
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
        elif not ctx.voice_client:
            logger.debug("🎵 [Music Service] Conectando nuevo wavelink.Player...")
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
        else:
            player = ctx.voice_client
            if not player.connected:
                logger.debug("🎵 [Music Service] wavelink.Player desconectado, reconectando...")
                await player.connect(cls=wavelink.Player, self_deaf=True, channel=ctx.author.voice.channel)
        
        if player.volume == 0:
            await player.set_volume(settings.LAVALINK_CONFIG.get("DEFAULT_VOLUME", 50))
            
        logger.debug("🎵 [Music Service] ensure_player completado exitosamente.")
        return player
    except asyncio.TimeoutError:
        logger.exception("❌ [Music Service] Timeout al conectar.")
        err_msg = "❌ **Error de Red:** El nodo público de Lavalink no pudo establecer conexión con los servidores de voz de Discord. Intenta de nuevo en unos segundos."
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), err_msg))
        return None
    except Exception as e:
        logger.exception("❌ [Music Service] Error inesperado en ensure_player.")
        voice_service.voice_targets.pop(ctx.guild.id, None)
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), str(e)))
        return None

async def send_now_playing(bot: discord.Client, player: wavelink.Player, track: wavelink.Playable):
    """Genera y envía el mensaje de 'Ahora suena' centralizando la lógica de UI."""
    logger.debug(f"🖼️ [Music Service] send_now_playing invocado para: {track.title}")
    if not hasattr(player, "home") or not player.home:
        logger.debug("🖼️ [Music Service] Abortado: Player no tiene 'home' configurado.")
        return

    # Lock para evitar que múltiples eventos on_track_start dupliquen el mensaje
    if not hasattr(player, "_msg_lock"):
        player._msg_lock = asyncio.Lock()

    async with player._msg_lock:
        lang = await lang_service.get_guild_lang(player.guild.id)
        
        # 1. Limpieza rigurosa del mensaje anterior
        if hasattr(player, "last_msg") and player.last_msg:
            try:
                old_msg = player.last_msg
                player.last_msg = None # Limpiar referencia antes del await
                await old_msg.delete()
            except: pass

        # 2. Actualizar Presencia del bot
        await update_presence(bot, player, track, lang)
        
        # 3. Enviar nuevo mensaje y guardar referencia
        embed = create_np_embed(player, track, lang)
        view = MusicControls(player, lang=lang)
        player.last_msg = await player.home.send(embed=embed, view=view)
        player.last_view = view

async def handle_enqueue(ctx, player: wavelink.Player, tracks: wavelink.Playable | wavelink.Playlist, lang: str):
    """Maneja la lógica de añadir pistas o playlists a la cola, optimizando el feedback al usuario."""
    logger.debug(f"📥 [Music Service] handle_enqueue invocado. Playlist: {isinstance(tracks, wavelink.Playlist)}")
    player.autoplay = wavelink.AutoPlayMode.disabled
    if isinstance(tracks, wavelink.Playlist):
        await _handle_playlist_enqueue(ctx, player, tracks, lang)
    else:
        await _handle_track_enqueue(ctx, player, tracks, lang)

def _is_duplicate(player: wavelink.Player, track: wavelink.Playable) -> bool:
    """Comprueba si una pista ya está en la cola o reproduciéndose."""
    if player.current and player.current.uri == track.uri:
        return True
    return any(t.uri == track.uri for t in player.queue)

async def _handle_playlist_enqueue(ctx, player, playlist, lang):
    if not playlist:
        return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_error", lang), lang_service.get_text("music_playlist_empty", lang)))
    
    playlist_label = lang_service.get_text("music_playlist_default", lang)
    added_count = 0
    for track in playlist:
        if _is_duplicate(player, track):
            continue
        track.requester = ctx.author
        await player.queue.put_wait(track)
        added_count += 1
        await asyncio.sleep(0)
        
    msg = lang_service.get_text("music_playlist_added", lang, name=playlist.name or playlist_label, count=added_count)
    await ctx.send(embed=embed_service.success(lang_service.get_text("music_queue_title", lang), msg, lite=True))
    
    if not player.playing and not player.queue.is_empty:
        await player.play(player.queue.get())

async def _handle_track_enqueue(ctx, player, tracks, lang):
    track = tracks[0] if isinstance(tracks, (list, tuple)) else tracks
    logger.debug(f"📥 [Music Service] _handle_track_enqueue para: {track.title}")
    track.requester = ctx.author
    if not player.playing:
        logger.debug(f"▶️ [Music Service] Reproductor inactivo. Forzando play: {track.title}")
        await player.play(track)
        msg = lang_service.get_text("music_playing", lang)
        await ctx.send(embed=embed_service.success(lang_service.get_text("music_now_playing_title", lang), f"{msg}: **{track.title}**", lite=True), delete_after=15)
    else:
        if _is_duplicate(player, track):
            logger.debug(f"⚠️ [Music Service] Pista duplicada detectada: {track.title}")
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("music_queue_title", lang), lang_service.get_text("music_error_duplicate", lang)), delete_after=10)
            
        logger.debug(f"⏸️ [Music Service] Reproductor activo. Añadiendo a la cola: {track.title}")
        await player.queue.put_wait(track)
        msg = lang_service.get_text("music_track_enqueued", lang, title=track.title)
        await ctx.send(embed=embed_service.success(lang_service.get_text("music_queue_title", lang), msg, lite=True))

async def handle_play_search(busqueda: str) -> wavelink.Playable | wavelink.Playlist | None:
    """Encapsula la lógica de búsqueda con fallback para el comando play."""
    # Soporte para URLs envueltas en <>
    if busqueda.startswith("<") and busqueda.endswith(">"):
        busqueda = busqueda[1:-1]
        
    logger.debug(f"🔎 [Music Service] Buscando: {busqueda}")
    if re.match(r'https?://(?:www\.)?.+', busqueda):
        logger.debug("🔎 [Music Service] URL detectada. Buscando directamente...")
        return await wavelink.Playable.search(busqueda)

    # Prioridad de búsqueda flexible basada en settings
    primary = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
    sources = list(dict.fromkeys([primary, "ytsearch", "scsearch"]))
    
    for source in sources:
        try:
            logger.debug(f"🔎 [Music Service] Intentando fuente: {source}")
            tracks = await wavelink.Playable.search(f"{source}:{busqueda}")
            if tracks:
                logger.debug(f"✅ [Music Service] Búsqueda exitosa en {source} ({len(tracks) if isinstance(tracks, list) else 'Playlist'} resultados)")
                return tracks
            logger.debug(f"⚠️ [Music Service] Sin resultados en {source}")
        except Exception:
            logger.exception(f"❌ [Music Service] Error buscando en {source}")
            continue
    logger.debug("❌ [Music Service] Todos los proveedores fallaron.")
    return None

async def handle_track_fallback(player: wavelink.Player, track: wavelink.Playable) -> bool:
    """Intenta encontrar una versión alternativa de una canción que falló."""
    uri = (track.uri or "").lower()
    # Si falló YouTube o Spotify (que resuelve a YT), probamos SoundCloud
    fallback_provider = "scsearch" if "youtube" in uri or "spotify" in uri else "ytsearch"
    
    logger.info(f"🔄 [Music Service] Fallback automático a {fallback_provider} para: {track.title}")
    
    try:
        clean_name = clean_track_title(track.title)
        query = f"{fallback_provider}:{clean_name} {track.author}"
        tracks = await wavelink.Playable.search(query)
        
        if tracks:
            new_track = tracks[0]
            new_track.requester = getattr(track, "requester", None)
            # Si el error ocurrió al final de la canción, empezamos desde el inicio
            pos = int(player.position)
            if track.length > 0 and pos > (track.length - 5000): pos = 0
            
            await player.play(new_track, start=pos)
            return True
    except Exception as e:
        logger.error(f"❌ Fallback fallido: {e}")
    
    return False

def get_music_error_message(error: Exception, lang: str) -> str:
    """Traduce excepciones técnicas a mensajes amigables para el usuario."""
    err_str = str(error)
    if "NoNodesAvailable" in err_str:
        return lang_service.get_text("music_err_lavalink_nodes", lang)
    
    if "FriendlyException" in err_str:
        if "403" in err_str or "confirm your age" in err_str:
            return lang_service.get_text("music_err_youtube_block", lang)
        return lang_service.get_text("music_err_load_failed", lang, error=err_str)
        
    if "SSLCertVerificationError" in err_str:
        return "❌ **Error de SSL:** El nodo de música tiene un certificado inválido."

    return lang_service.get_text("music_err_generic", lang, error=err_str)

async def save_player_state(player: wavelink.Player):
    """Extrae y guarda el estado del player en la base de datos."""
    if not player or not player.connected or not player.current:
        return

    data = {
        "voice_channel_id": player.channel.id,
        "text_channel_id": player.home.id if hasattr(player, "home") and player.home else 0,
        "current_track_uri": player.current.uri,
        "position": int(player.position),
        "volume": player.volume,
        "queue_uris": [t.uri for t in player.queue if t.uri],
        "smart_autoplay": getattr(player, "smart_autoplay", False)
    }
    await persistence_service.store("music", player.guild.id, data)

async def restore_players(bot):
    """Busca sesiones guardadas y las reanuda."""
    await bot.wait_until_ready()
    # Esperar un poco a que los nodos Lavalink conecten
    await asyncio.sleep(5)
    
    records = await persistence_service.load_all("music")
    if not records:
        return

    logger.debug(f"🔄 [Music Service] Restaurando {len(records)} sesiones de música...")

    for guild_id, data in records.items():
        guild = bot.get_guild(int(guild_id))
        if not guild: continue

        v_channel = guild.get_channel(data['voice_channel_id'])
        t_channel = guild.get_channel(data['text_channel_id'])
        if not v_channel: continue

        try:
            player: wavelink.Player = await v_channel.connect(cls=wavelink.Player, self_deaf=True)
            await player.set_volume(data['volume'])
            player.home = t_channel
            player.smart_autoplay = data.get('smart_autoplay', False)

            # Restaurar canción actual
            tracks = await wavelink.Playable.search(data['current_track_uri'])
            if tracks:
                current = tracks[0]
                await player.play(current, start=data['position'])

            # Restaurar cola (en segundo plano para no bloquear)
            for uri in data.get('queue_uris', []):
                t = await wavelink.Playable.search(uri)
                if t: await player.queue.put_wait(t[0])
            
            logger.debug(f"✅ Sesión restaurada en {guild.name}")
        except Exception:
            logger.exception(f"❌ Error restaurando sesión en {guild.id}")
        finally:
            await persistence_service.clear("music", guild.id)

async def connect_nodes(bot):
    """Configura y conecta al primer nodo disponible (Failover)."""
    await bot.wait_until_ready()
    
    node_config = settings.LAVALINK_CONFIG
    node_configs = []
    if "NODES" in node_config:
        node_configs = list(node_config["NODES"])
    elif "HOST" in node_config:
        node_configs = [node_config]

    await connect_best_node(bot, node_configs)

async def connect_best_node(bot, node_configs, max_retries=3):
    """Itera sobre los nodos configurados hasta conectar uno."""
    global _is_connecting
    if _is_connecting or not node_configs:
        return
    
    _is_connecting = True
    try:
        for i in range(max_retries):
            if wavelink.Pool.nodes:
                for node in wavelink.Pool.nodes.values():
                    if node.status == wavelink.NodeStatus.CONNECTED:
                        return

            logger.debug(f"🔄 [Music Service] Intento de conexión {i+1}/{max_retries}...")

            for config in node_configs:
                identifier = config.get("IDENTIFIER", config["HOST"])
                
                if identifier in wavelink.Pool.nodes:
                    old_node = wavelink.Pool.get_node(identifier)
                    if old_node.status == wavelink.NodeStatus.CONNECTED and i == 0:
                        return
                    
                    logger.debug(f"🧹 [Music Service] Limpiando nodo antiguo: {identifier}")
                    await old_node.close()

                try:
                    protocol = "https" if config.get("SECURE") else "http"
                    node = wavelink.Node(
                        identifier=identifier,
                        uri=f"{protocol}://{config['HOST']}:{config['PORT']}",
                        password=config['PASSWORD']
                    )
                    
                    await wavelink.Pool.connect(nodes=[node], client=bot, cache_capacity=settings.LAVALINK_CONFIG.get("CACHE_CAPACITY", 100))
                    
                    try:
                        def check(p): return p.node.identifier == identifier and p.node.status == wavelink.NodeStatus.CONNECTED
                        await bot.wait_for('wavelink_node_ready', check=check, timeout=10.0)
                        return 
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ [Music Service] Nodo {identifier} no respondió. Cerrando...")
                        node = wavelink.Pool.nodes.get(identifier)
                        if node: await node.close()
                            
                except Exception:
                    logger.exception(f"❌ [Music Service] Error nodo {identifier}")
            
            if i < max_retries - 1:
                await asyncio.sleep(5)
    finally:
        _is_connecting = False

async def get_search_choices(current: str) -> list[app_commands.Choice[str]]:
    """Genera opciones para el autocompletado de búsqueda."""
    if not wavelink.Pool.nodes or not current:
        return []
    try:
        # Prioridad de Autocompletado: Siempre Spotify primero si está configurado
        primary = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
        sources = [primary, "ytsearch", "scsearch"]
        sources = list(dict.fromkeys(sources))
        
        tracks = []
        
        for source in sources:
            try:
                tracks = await wavelink.Playable.search(f"{source}:{current}")
                if tracks:
                    logger.debug(f"🔎 [Music Service] Autocompletado resuelto vía: {source}")
                    break
                else:
                    logger.debug(f"⚠️ [Music Service] {source} no devolvió resultados para '{current}'")
            except Exception as e:
                logger.debug(f"⚠️ [Music Service] Autocompletado falló para fuente {source}: {e}")
                continue

        if not tracks: return []
        
        choices = []
        for track in tracks[:settings.MUSIC_CONFIG["AUTOCOMPLETE_LIMIT"]]:
            duration = "LIVE" if track.is_stream else format_duration(track.length)
            title_limit = settings.MUSIC_CONFIG["AUTOCOMPLETE_TITLE_LIMIT"]
            author_limit = settings.MUSIC_CONFIG["AUTOCOMPLETE_AUTHOR_LIMIT"]
            name = f"[{duration}] {track.title[:title_limit]} - {track.author[:author_limit]}"
            choices.append(app_commands.Choice(name=name, value=track.uri or track.title))
        return choices
    except Exception as e:
        logger.debug(f"Error en autocompletado de música: {e}")
        return []

async def check_voice(ctx) -> bool:
    """Verifica si el usuario puede ejecutar comandos de control."""
    lang = await lang_service.get_guild_lang(ctx.guild.id)
    player = ctx.voice_client
    
    if not player or not player.connected:
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
        return False
        
    if not ctx.author.voice or (player.channel and ctx.author.voice.channel.id != player.channel.id):
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_control_voice_error", lang), lite=True), ephemeral=True)
        return False
    return True

async def apply_filter(player: wavelink.Player, filter_name: str) -> bool:
    """Aplica un preset de filtros al reproductor."""
    config = FILTERS_CONFIG.get(filter_name.lower())
    if not config: return False

    filters = wavelink.Filters()
    
    # Si es 'flat' o 'clear', enviamos filtros vacíos para resetear
    if config["type"] == "clear":
        await player.set_filters(filters)
        return True

    if config["type"] == "equalizer":
        # Wavelink 3.x: Usar .set() con lista de diccionarios
        bands = [{"band": b, "gain": g} for b, g in config["bands"]]
        filters.equalizer.set(bands=bands)
    
    elif config["type"] == "timescale":
        filters.timescale.set(
            speed=config.get("speed", 1.0),
            pitch=config.get("pitch", 1.0)
        )
    
    elif config["type"] == "rotation":
        filters.rotation.set(rotation_hz=config.get("rotation_hz", 0.2))
        
    elif config["type"] == "karaoke":
        filters.karaoke.set(
            level=1.0,
            mono_level=1.0,
            filter_band=220.0,
            filter_width=100.0
        )
        
    elif config["type"] == "tremolo":
        filters.tremolo.set(
            frequency=config.get("frequency", 2.0),
            depth=config.get("depth", 0.5)
        )
        
    elif config["type"] == "lowpass":
        filters.low_pass.set(smoothing=config.get("smoothing", 20.0))
        
    elif config["type"] == "vibrato":
        filters.vibrato.set(
            frequency=config.get("frequency", 2.0),
            depth=config.get("depth", 0.5)
        )

    await player.set_filters(filters)
    return True

async def fade_in(player: wavelink.Player, duration_ms: int):
    """Simula un efecto de Fade-In ajustando el volumen gradualmente."""
    target_vol = player.volume
    if target_vol == 0: return
    if player.current and player.current.length < duration_ms: return

    last_set_vol = 0
    current_track = player.current
    
    await player.set_volume(0)
    
    steps = settings.MUSIC_CONFIG["FADE_IN_STEPS"]
    step_delay = (duration_ms / 1000) / steps
    vol_step = target_vol / steps
    
    # Optimización: Evitar sleeps demasiado cortos que quemen CPU
    if step_delay < 0.05:
        step_delay = 0.05
    
    for i in range(1, steps + 1):
        if not player.playing or player.current != current_track: return

        try:
            if not player.connected or player.paused: return
            if last_set_vol > 0 and abs(player.volume - last_set_vol) > settings.MUSIC_CONFIG["VOLUME_TOLERANCE"]: return

            await asyncio.sleep(step_delay)
            new_vol = int(vol_step * i)
            await player.set_volume(new_vol)
            last_set_vol = new_vol
        except Exception:
            return
    
    await player.set_volume(target_vol)

def get_queue_pages(player: wavelink.Player, lang: str) -> list[discord.Embed]:
    """Genera las páginas de embeds para la cola de reproducción."""
    if not player or (not player.current and player.queue.is_empty):
        return []

    pages = []
    queue_list = list(player.queue)
    chunk_size = settings.MUSIC_CONFIG["QUEUE_PAGE_SIZE"]
    chunks = [queue_list[i:i + chunk_size] for i in range(0, len(queue_list), chunk_size)]

    if not chunks and player.current:
        chunks = [[]]

    for i, chunk in enumerate(chunks):
        desc = ""
        if player.current:
            desc += lang_service.get_text("music_queue_current", lang, title=player.current.title) + "\n\n"
        
        if chunk:
            desc += lang_service.get_text("music_queue_next", lang) + "\n"
            for j, track in enumerate(chunk):
                idx = (i * chunk_size) + j + 1
                desc += f"`{idx}.` {track.title} - *{track.author}*\n"
        
        embed = discord.Embed(title=lang_service.get_text("music_queue_title", lang), description=desc, color=settings.COLORS["INFO"])
        embed.set_footer(text=lang_service.get_text("music_queue_footer", lang, current=i+1, total=len(chunks), tracks=len(player.queue)))
        pages.append(embed)
    
    return pages

async def sync_ui(player: wavelink.Player):
    """Sincroniza el estado visual de la última vista activa del reproductor."""
    view = getattr(player, "last_view", None)
    msg = getattr(player, "last_msg", None)
    if view and msg:
        view._sync_state()
        try:
            await msg.edit(view=view)
        except discord.HTTPException:
            pass
