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
        details=f"👤 {track.author}",
        state=f"💿 {album_name} | 🔊 {player.volume}%",
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

    # 2. Deshabilitar botones visualmente
    view = getattr(player, "last_view", None)
    if view:
        for child in view.children:
            child.disabled = True
        
        if not skip_message_edit:
            msg = getattr(player, "last_msg", None)
            try:
                if msg: await msg.edit(view=view)
            except (discord.HTTPException, discord.Forbidden): pass
        view.stop()
    
    # Limpiar referencias
    player.last_view = None
    player.home = None # Liberar referencia al canal de texto
    
    # Limpiar cola
    if hasattr(player, "queue"):
        try: player.queue.clear()
        except: pass
        
    # Resetear estados internos
    player.smart_autoplay = False
    player.last_track_error = False
    player.last_msg = None

async def ensure_player(ctx, lang: str) -> wavelink.Player | None:
    """Asegura que el bot esté conectado correctamente y retorna el player."""
    if not ctx.author.voice:
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_join", lang)))
        return None

    permissions = ctx.author.voice.channel.permissions_for(ctx.guild.me)
    if not permissions.connect or not permissions.speak:
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("voice_error_perms", lang)))
        return None

    try:
        if ctx.voice_client and not isinstance(ctx.voice_client, wavelink.Player):
            await ctx.voice_client.disconnect(force=True)
            player = await ctx.author.voice.channel.connect(cls=SafePlayer, self_deaf=True)
        elif not ctx.voice_client:
            player = await ctx.author.voice.channel.connect(cls=SafePlayer, self_deaf=True)
        else:
            player = ctx.voice_client
            if not player.connected:
                await player.connect(cls=SafePlayer, self_deaf=True, channel=ctx.author.voice.channel)
        
        if player.volume == 0:
            await player.set_volume(settings.LAVALINK_CONFIG.get("DEFAULT_VOLUME", 50))
            
        return player
    except Exception as e:
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), str(e)))
        return None

async def send_now_playing(bot: discord.Client, player: wavelink.Player, track: wavelink.Playable):
    """Genera y envía el mensaje de 'Ahora suena' centralizando la lógica de UI."""
    if not hasattr(player, "home") or not player.home:
        return

    lang = await lang_service.get_guild_lang(player.guild.id)
    embed = create_np_embed(player, track, lang)
    view = MusicControls(player, lang=lang)
    
    # Limpieza de mensajes anteriores para evitar spam
    if hasattr(player, "last_msg") and player.last_msg:
        try: await player.last_msg.delete()
        except: pass

    # Actualizar Presencia del bot
    await update_presence(bot, player, track, lang)
    
    # Enviar nuevo mensaje y guardar referencia
    player.last_msg = await player.home.send(embed=embed, view=view)

async def handle_enqueue(ctx, player: wavelink.Player, tracks: wavelink.Playable | wavelink.Playlist, lang: str):
    """Maneja la lógica de añadir pistas o playlists a la cola, optimizando el feedback al usuario."""
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
    await ctx.send(embed=embed_service.success(lang_service.get_text("title_queue", lang), msg, lite=True))
    
    if not player.playing and not player.queue.is_empty:
        await player.play(player.queue.get())

async def _handle_track_enqueue(ctx, player, tracks, lang):
    track = tracks[0] if isinstance(tracks, (list, tuple)) else tracks
    track.requester = ctx.author
    if not player.playing:
        await player.play(track)
        msg = lang_service.get_text("music_playing", lang)
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), f"{msg}: **{track.title}**", lite=True), delete_after=15)
    else:
        if _is_duplicate(player, track):
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_music", lang), lang_service.get_text("music_error_duplicate", lang)), delete_after=10)
            
        await player.queue.put_wait(track)
        msg = lang_service.get_text("music_track_enqueued", lang, title=track.title)
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_queue", lang), msg, lite=True))

async def handle_play_search(busqueda: str) -> wavelink.Playable | wavelink.Playlist | None:
    """Encapsula la lógica de búsqueda con fallback para el comando play."""
    # Soporte para URLs envueltas en <>
    if busqueda.startswith("<") and busqueda.endswith(">"):
        busqueda = busqueda[1:-1]
        
    if re.match(r'https?://(?:www\.)?.+', busqueda):
        return await wavelink.Playable.search(busqueda)

    # Prioridad de búsqueda flexible basada en settings
    primary = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
    sources = list(dict.fromkeys([primary, "ytsearch", "scsearch"]))
    
    for source in sources:
        try:
            tracks = await wavelink.Playable.search(f"{source}:{busqueda}")
            if tracks:
               # logger.debug(f"🔍 [Music Service] Búsqueda resuelta vía {source}")
                return tracks
        except Exception:
            continue
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
            await player.play(new_track, start=int(player.position))
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
            player: wavelink.Player = await v_channel.connect(cls=SafePlayer, self_deaf=True)
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
                    old_node = wavelink.Pool.get_node(identifier=identifier)
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

class SafePlayer(wavelink.Player):
    """
    Player personalizado que captura errores de conexión con el nodo (ej. 500 Internal Server Error)
    durante la actualización del servidor de voz, evitando que el bot crashee o quede en estado zombie.
    """
    async def on_voice_server_update(self, data: dict):
        try:
            await super().on_voice_server_update(data)
        except Exception as e:
            logger.warning(f"⚠️ [SafePlayer] Fallo al enviar actualización de voz al nodo: {e}")
            # Si el nodo rechaza la conexión, desconectamos localmente para limpiar estado
            try: await self.disconnect()
            except: pass
