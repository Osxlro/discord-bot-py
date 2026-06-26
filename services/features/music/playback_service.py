import logging
import asyncio
import discord
import re
import wavelink
from discord import app_commands
from config import settings
from services.core import lang_service, persistence_service
from services.utils import embed_service
from ui.music.music_ui import MusicControls, create_np_embed, format_duration
from services.features.music import queue_service, presence_service

logger = logging.getLogger(__name__)

def clean_track_title(title: str) -> str:
    """Limpia metadatos innecesarios de los títulos para mejorar la precisión de búsqueda."""
    if not title: return ""
    title = re.sub(r"[\(\[].*?[\)\]]", "", title)
    noise = ["official video", "official audio", "lyrics", "hd", "4k", "video oficial", "letra", "full hd", "audio"]
    for n in noise:
        title = re.compile(re.escape(n), re.IGNORECASE).sub("", title)
    return title.strip()

async def send_now_playing(bot: discord.Client, player: wavelink.Player, track: wavelink.Playable, new_track=True):
    """
    Genera y envía el mensaje 'Ahora Suena', optimizando la edición de mensajes.
    `new_track=True` fuerza el borrado y re-envío del mensaje.
    """
    try:
        guild_id = player.guild.id
        data = queue_service.get_player_data(guild_id)
        home = getattr(player, "home", None) or data.get("home")
        if not home:
            # Fallback dinámico si por alguna razón 'home' es None pero el bot está reproduciendo en un servidor
            guild = bot.get_guild(guild_id)
            if guild:
                # 1. Intentar el system_channel
                if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                    home = guild.system_channel
                else:
                    # 2. Buscar el primer canal de texto disponible donde tengamos permisos de envío
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            home = channel
                            break
            
            if home:
                logger.warning(f"⚠️ [Music Service] 'home' era None en guild {guild_id}. Se usó el canal fallback: {home.name}")
                # Guardar el fallback para futuras reproducciones de la sesión
                player.home = home
                data["home"] = home
            else:
                logger.warning(f"⚠️ [Music Service] No se pudo enviar 'Ahora suena' porque 'home' es None en el guild {guild_id} y no se encontró canal fallback.")
                return

        lang = await lang_service.get_guild_lang(guild_id)
        embed = create_np_embed(player, track, lang)
        view = MusicControls(player, lang=lang)

        last_msg = getattr(player, "last_msg", None) or data.get("last_msg")

        if new_track or not last_msg or last_msg.author.id != bot.user.id:
            if last_msg:
                try: await last_msg.delete()
                except Exception: pass
            
            sent_msg = await home.send(embed=embed, view=view)
            player.last_msg = sent_msg
            data["last_msg"] = sent_msg
        else:
            try:
                await last_msg.edit(embed=embed, view=view)
            except Exception as e:
                logger.warning(f"No se pudo editar el mensaje del reproductor: {e}. Enviando uno nuevo.")
                try: await last_msg.delete()
                except Exception: pass
                sent_msg = await home.send(embed=embed, view=view)
                player.last_msg = sent_msg
                data["last_msg"] = sent_msg
        
        player.last_view = view
        data["last_view"] = view
        await presence_service.update_presence(bot, player, track, lang)
    except Exception as e:
        logger.exception(f"🔥 Error en send_now_playing: {e}")

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
    if busqueda.startswith("<") and busqueda.endswith(">"):
        busqueda = busqueda[1:-1]
        
    logger.debug(f"🔎 [Music Service] Buscando: {busqueda}")
    if re.match(r'https?://(?:www\.)?.+', busqueda):
        logger.debug("🔎 [Music Service] URL detectada. Buscando directamente...")
        return await wavelink.Playable.search(busqueda)

    primary = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
    sources = list(dict.fromkeys([primary, "ytsearch", "scsearch"]))
    
    for source in sources:
        try:
            logger.debug(f"🔎 [Music Service] Intentando fuente: {source}")
            tracks = await wavelink.Playable.search(busqueda, source=source)
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
    fallback_provider = "scsearch" if "youtube" in uri or "spotify" in uri else "ytsearch"
    
    logger.info(f"🔄 [Music Service] Fallback automático a {fallback_provider} para: {track.title}")
    
    try:
        clean_name = clean_track_title(track.title)
        query = f"{clean_name} {track.author}"
        tracks = await wavelink.Playable.search(query, source=fallback_provider)
        
        if tracks:
            new_track = tracks[0]
            new_track.requester = getattr(track, "requester", None)
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

async def get_search_choices(current: str) -> list[app_commands.Choice[str]]:
    """Genera opciones para el autocompletado de búsqueda."""
    if not wavelink.Pool.nodes or not current:
        return []
    try:
        primary = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
        sources = [primary, "ytsearch", "scsearch"]
        sources = list(dict.fromkeys(sources))
        
        tracks = []
        
        for source in sources:
            try:
                tracks = await wavelink.Playable.search(current, source=source)
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
