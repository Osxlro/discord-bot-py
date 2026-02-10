import discord
import asyncio
import wavelink
import logging
import random
import re
from discord import app_commands
from discord.ext import commands, tasks
from config import settings
from services import embed_service, lang_service, pagination_service, algorithm_service, db_service, music_service

logger = logging.getLogger(__name__)

URL_RX = re.compile(r'https?://(?:www\.)?.+')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recommender = algorithm_service.RecommendationEngine()
        self.node_configs = []
        self._is_connecting = False

    async def cog_load(self):
        """Conecta a Lavalink al cargar el Cog."""
        # Usamos create_task para no bloquear el arranque del bot si Lavalink está caído
        self.bot.loop.create_task(self.connect_nodes())
        self.node_monitor.start()

    async def cog_unload(self):
        self.node_monitor.cancel()

    async def connect_nodes(self):
        """Configura y conecta al primer nodo disponible (Failover)."""
        await self.bot.wait_until_ready()
        
        # Cargar lista de nodos
        node_config = settings.LAVALINK_CONFIG
        if "NODES" in node_config:
            self.node_configs = list(node_config["NODES"])
        elif "HOST" in node_config:
            self.node_configs = [node_config]

        await self.connect_best_node()

    async def connect_best_node(self, max_retries=3):
        """Itera sobre los nodos configurados hasta conectar uno."""
        if self._is_connecting or not self.node_configs:
            return
        
        self._is_connecting = True
        try:
            for i in range(max_retries):
                # Si ya hay un nodo conectado, terminamos
                if wavelink.Pool.nodes:
                    for node in wavelink.Pool.nodes.values():
                        if node.status == wavelink.NodeStatus.CONNECTED:
                            return

                logger.info(f"🔄 [Music] Intento de conexión {i+1}/{max_retries}...")

                for config in self.node_configs:
                    identifier = config.get("IDENTIFIER", config["HOST"])
                    
                    # Limpieza preventiva de nodos zombies
                    existing = wavelink.Pool.nodes.get(identifier)
                    if existing:
                        if existing.status == wavelink.NodeStatus.CONNECTED:
                            return
                        # Cerrar nodo si está en estado desconectado/conectando para evitar fugas
                        await existing.close()

                    try:
                        protocol = "https" if config.get("SECURE") else "http"
                        node = wavelink.Node(
                            identifier=identifier,
                            uri=f"{protocol}://{config['HOST']}:{config['PORT']}",
                            password=config['PASSWORD']
                        )
                        
                        # Intentar conectar SOLO este nodo
                        await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=settings.LAVALINK_CONFIG.get("CACHE_CAPACITY", 100))
                        
                        # Esperar confirmación (Timeout corto para evitar bloqueos)
                        try:
                            def check(p): return p.node.identifier == identifier and p.node.status == wavelink.NodeStatus.CONNECTED
                            await self.bot.wait_for('wavelink_node_ready', check=check, timeout=10.0)
                            
                            # Si conecta, aseguramos que el monitor esté corriendo
                            if not self.node_monitor.is_running():
                                self.node_monitor.start()
                            return # Éxito, salimos del bucle
                        except asyncio.TimeoutError:
                            logger.warning(f"⚠️ [Music] Nodo {identifier} no respondió. Cerrando...")
                            node = wavelink.Pool.nodes.get(identifier)
                            if node: await node.close() # Matar reintentos
                            
                    except Exception as e:
                        logger.error(f"❌ [Music] Error nodo {identifier}: {e}")
                
                if i < max_retries - 1:
                    await asyncio.sleep(5)
            
            # Si fallan todos los intentos
            logger.error("❌ [Music] No se pudo conectar a Lavalink. Deteniendo reintentos automáticos.")
            if self.node_monitor.is_running():
                self.node_monitor.cancel()
        finally:
            self._is_connecting = False

    @tasks.loop(minutes=1)
    async def node_monitor(self):
        """Monitorea el estado de los nodos y reconecta si es necesario."""
        await self.bot.wait_until_ready()
        
        # Verificar si hay nodos conectados
        if wavelink.Pool.nodes:
             if any(node.status == wavelink.NodeStatus.CONNECTED for node in wavelink.Pool.nodes.values()):
                 return

        logger.warning("⚠️ [Music] Monitor: Nodos desconectados. Intentando reconectar (1 intento)...")
        # Solo 1 intento en el monitor periódico para no saturar logs
        await self.connect_best_node(max_retries=1)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"✅ [Music] Nodo Lavalink conectado: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_node_closed(self, node: wavelink.Node, payload: wavelink.NodeClosedEventPayload = None):
        """Detecta caída de nodo y activa Failover."""
        logger.warning(f"⚠️ [Music] Nodo {node.identifier} desconectado. Iniciando Failover...")
        await asyncio.sleep(1)
        await self.connect_best_node()

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        """Maneja errores de reproducción saltando la pista."""
        logger.warning(f"⚠️ [Music] Excepción en pista ({payload.track.title}): {payload.exception}")
        
        player = payload.player
        if not player: return

        # Guardamos la posición actual para intentar reanudar ahí (Smart Seek)
        current_position = int(player.position) if player else 0

        # --- FALLBACK SYSTEM ---
        # Si YouTube falla (bloqueo/streams), intentamos SoundCloud automáticamente.
        err_msg = str(payload.exception)
        is_yt_error = "No supported audio streams" in err_msg or "403" in err_msg or "not available" in err_msg
        is_yt_track = "youtube.com" in (payload.track.uri or "") or "youtu.be" in (payload.track.uri or "")

        if is_yt_error and is_yt_track:
            logger.info(f"🔄 [Music] Error de YouTube detectado. Intentando fallback a SoundCloud...")
            try:
                # Búsqueda espejo en SoundCloud
                query = f"scsearch:{payload.track.title} {payload.track.author}"
                tracks = await wavelink.Playable.search(query)
                
                if tracks:
                    fallback_track = tracks[0]
                    # Preservar quién pidió la canción original
                    if hasattr(payload.track, "requester"):
                        fallback_track.requester = payload.track.requester
                    
                    # Reproducir desde donde se quedó (si es posible)
                    await player.play(fallback_track, start=current_position)
                    
                    # Aviso temporal al usuario
                    lang = await lang_service.get_guild_lang(player.guild.id)
                    if hasattr(player, "home") and player.home:
                        try:
                            await player.home.send(embed=embed_service.warning(lang_service.get_text("title_info", lang), f"⚠️ YouTube bloqueó la reproducción. Intentando desde SoundCloud:\n🎵 **{fallback_track.title}**", lite=True), delete_after=10)
                        except discord.HTTPException:
                            pass
                    return # ¡Importante! Salimos para evitar el stop() de abajo
            except Exception as e:
                logger.error(f"❌ Fallback fallido: {e}")

        # Si no es recuperable o falló el fallback
        player.last_track_error = True
        await player.stop() # Dispara track_end para seguir con la cola

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload):
        """Maneja pistas atascadas saltando la pista."""
        logger.warning(f"⚠️ [Music] Pista atascada: {payload.track.title}")
        if payload.player:
            payload.player.last_track_error = True
            await payload.player.stop()

    async def play_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        # Evitar errores si Lavalink no está conectado
        if not wavelink.Pool.nodes:
            return []
            
        if not current:
            return []
        try:
            # Búsqueda rápida en YouTube para autocompletado
            provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "yt")
            tracks = await wavelink.Playable.search(f"{provider}search:{current}")
            if not tracks: return [] # Maneja None y lista vacía
            choices = []
            for track in tracks[:settings.MUSIC_CONFIG["AUTOCOMPLETE_LIMIT"]]:
                if track.is_stream:
                    duration = "LIVE" # Se usará texto localizado en display, aquí es solo para autocomplete
                else:
                    duration = music_service.format_duration(track.length)
                
                title_limit = settings.MUSIC_CONFIG["AUTOCOMPLETE_TITLE_LIMIT"]
                author_limit = settings.MUSIC_CONFIG["AUTOCOMPLETE_AUTHOR_LIMIT"]
                name = f"[{duration}] {track.title[:title_limit]} - {track.author[:author_limit]}"
                choices.append(app_commands.Choice(name=name, value=track.uri or track.title))
            return choices
        except Exception as e:
            logger.debug(f"Error en autocompletado de música: {e}")
            return []

    @commands.hybrid_command(name="play", description="Reproduce música desde YouTube, SoundCloud, etc.")
    @app_commands.describe(busqueda="Nombre de la canción o URL")
    @app_commands.autocomplete(busqueda=play_autocomplete)
    async def play(self, ctx: commands.Context, busqueda: str):
        # Deferimos la interacción al inicio para evitar timeouts si la conexión tarda
        busqueda = busqueda.strip()
        lang = await lang_service.get_guild_lang(ctx.guild.id)

        # Verificación y conexión bajo demanda si los nodos están caídos
        if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
            await ctx.send(embed=embed_service.info(lang_service.get_text("title_info", lang), "🔄 Conectando a servicios de música...", lite=True))
            await self.connect_best_node(max_retries=3)
            
            if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
                return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_err_lavalink_nodes", lang)))

        if not busqueda:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_error", lang), lang_service.get_text("error_missing_args", lang)))

        await ctx.defer()

        
        # 1. Verificar canal de voz
        if not ctx.author.voice:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_join", lang)))

        # 1.5 Verificar permisos del bot en el canal
        permissions = ctx.author.voice.channel.permissions_for(ctx.guild.me)
        if not permissions.connect or not permissions.speak:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("voice_error_perms", lang)))

        # 2. Obtener o crear Player
        try:
            # Verificar si existe un cliente de voz y si es del tipo correcto (Wavelink Player)
            if ctx.voice_client and not isinstance(ctx.voice_client, wavelink.Player):
                await ctx.voice_client.disconnect(force=True)
                player: wavelink.Player = await ctx.author.voice.channel.connect(cls=music_service.SafePlayer, self_deaf=True)
                await player.set_volume(settings.LAVALINK_CONFIG.get("DEFAULT_VOLUME", 50))
            
            elif not ctx.voice_client:
                player: wavelink.Player = await ctx.author.voice.channel.connect(cls=music_service.SafePlayer, self_deaf=True)
                await player.set_volume(settings.LAVALINK_CONFIG.get("DEFAULT_VOLUME", 50))
            
            else:
                player: wavelink.Player = ctx.voice_client
                if not player.connected:
                    await player.connect(cls=music_service.SafePlayer, self_deaf=True, channel=ctx.author.voice.channel)
                    # No reseteamos volumen aquí si ya existía el player, para mantener preferencia de usuario
        except Exception as e:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), str(e)))

        # 2.5 Ajustes post-conexión
        if player.connected:
            # Si el bot está muteado (por ejemplo, por /join de voice.py), lo desmuteamos
            if ctx.guild.me.voice.self_mute:
                await ctx.guild.me.edit(mute=False)
            
            # Si el usuario está en otro canal, movemos al bot
            if player.channel and ctx.author.voice.channel.id != player.channel.id:
                try:
                    await player.move_to(ctx.author.voice.channel)
                    # Actualizar target de Voice cog si existe para evitar que intente devolverlo
                    voice_cog = self.bot.get_cog("Voice")
                    if voice_cog and hasattr(voice_cog, 'voice_targets'):
                        voice_cog.voice_targets[ctx.guild.id] = ctx.author.voice.channel.id
                except Exception as e:
                    return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), str(e)))

        # Guardamos el canal de texto para enviar mensajes de "Now Playing"
        player.home = ctx.channel

        # 3. Lógica de Búsqueda (Con Fallback)
        # Soporte para URLs envueltas en <> (Discord suppress embed)
        if busqueda.startswith("<") and busqueda.endswith(">"):
            busqueda = busqueda[1:-1]
            
        is_url = URL_RX.match(busqueda)
        tracks = None

        try:
            if is_url:
                tracks = await wavelink.Playable.search(busqueda)
            else:
                # Estrategia de Fallback: YT -> SC
                default = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "yt")
                sources = [default]
                if default == "yt": sources.append("sc")
                elif default == "sc": sources.append("yt")
                
                last_err = None
                
                for source in sources:
                    try:
                        query = f"{source}search:{busqueda}"
                        tracks = await wavelink.Playable.search(query)
                        if tracks: 
                            break
                    except Exception as e:
                        last_err = e
                        logger.debug(f"⚠️ Fallo búsqueda en {source} ('{busqueda}'): {e}")
                        continue
                
                # Si fallaron todos los intentos y hubo error, lo lanzamos
                if not tracks and last_err:
                    raise last_err

            if not tracks:
                return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_music", lang), lang_service.get_text("music_search_empty", lang, query=busqueda or "Unknown")))

            # 4. Reproducir o Encolar (Soporte Playlist)
            # Asegurar que el modo nativo de autoplay esté desactivado para evitar conflictos
            player.autoplay = wavelink.AutoPlayMode.disabled

            if isinstance(tracks, wavelink.Playlist):
                # FIX: Evitar bloqueo si la playlist está vacía
                if not tracks:
                    return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_error", lang), "Playlist is empty."))

                for track in tracks:
                    track.requester = ctx.author
                    await player.queue.put_wait(track)
                    # Ceder control al loop para evitar bloqueos en playlists masivas
                    await asyncio.sleep(0)
                
                msg = lang_service.get_text("music_playlist_added", lang, name=tracks.name or "Playlist", count=len(tracks))
                await ctx.send(embed=embed_service.success(lang_service.get_text("title_queue", lang), msg, lite=True))
                
                if not player.playing:
                    first_track = player.queue.get()
                    await player.play(first_track)
                    # Confirmación visual de lo que empieza a sonar (UX)
                    msg_np = lang_service.get_text("music_playing", lang)
                    await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), f"{msg_np}: **{first_track.title}**", lite=True), delete_after=15)
            else:
                track = tracks[0]
                track.requester = ctx.author
                if not player.playing:
                    await player.play(track)
                    # Confirmación visual para cerrar la interacción deferred
                    msg = lang_service.get_text("music_playing", lang)
                    await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), f"{msg}: **{track.title}**", lite=True), delete_after=15)
                else:
                    await player.queue.put_wait(track)
                    msg = lang_service.get_text("music_track_enqueued", lang, title=track.title)
                    await ctx.send(embed=embed_service.success(lang_service.get_text("title_queue", lang), msg, lite=True))
        
        except Exception as e:
            logger.error(f"Error en comando play: {e}")
            
            err_str = str(e)
            if "NoNodesAvailable" in err_str:
                msg = lang_service.get_text("music_err_lavalink_nodes", lang)
            elif "FriendlyException" in err_str and "Something went wrong" in err_str:
                msg = lang_service.get_text("music_err_youtube_block", lang)
            elif "FriendlyException" in err_str:
                msg = lang_service.get_text("music_err_load_failed", lang, error=err_str)
            elif "SSLCertVerificationError" in err_str or "CERTIFICATE_VERIFY_FAILED" in err_str:
                msg = "❌ **Error de Nodo:** El certificado SSL del servidor de música ha expirado. Por favor cambia el nodo en `settings.py` (Usa puerto 2333 o cambia de host)."
            else:
                msg = lang_service.get_text("music_err_generic", lang, error=err_str)
                
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg))

    @commands.hybrid_command(name="stop", description="Detiene la música y desconecta al bot.")
    async def stop(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return

        player = ctx.voice_client
        if player:
            # Usar helper de limpieza del servicio
            await music_service.cleanup_player(self.bot, player)

            if player.connected:
                await player.disconnect()
            msg = lang_service.get_text("music_stopped", lang)
            await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), msg, lite=True))
        else:
            msg = lang_service.get_text("music_error_nothing", lang)
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg, lite=True), ephemeral=True)

    @commands.hybrid_command(name="skip", description="Salta la canción actual.")
    async def skip(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return

        if ctx.voice_client and ctx.voice_client.playing and ctx.voice_client.current:
            # Registrar feedback negativo para el algoritmo
            if ctx.voice_client.current:
                await db_service.record_song_feedback(ctx.guild.id, ctx.voice_client.current.identifier, is_skip=True)
            await ctx.voice_client.skip(force=True)
            msg = lang_service.get_text("music_skipped", lang)
            await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), msg, lite=True))
        else:
            msg = lang_service.get_text("music_error_nothing", lang)
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg, lite=True), ephemeral=True)

    @commands.hybrid_command(name="queue", description="Muestra la cola de reproducción.")
    async def queue(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        player: wavelink.Player = ctx.voice_client
        
        if not player or (not player.current and player.queue.is_empty):
            msg = lang_service.get_text("music_error_nothing", lang)
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_queue", lang), msg, lite=True))

        # Construcción de páginas para el Paginator
        pages = []
        queue_list = list(player.queue)
        chunk_size = settings.MUSIC_CONFIG["QUEUE_PAGE_SIZE"]
        chunks = [queue_list[i:i + chunk_size] for i in range(0, len(queue_list), chunk_size)]

        # Si la cola está vacía pero hay canción sonando (caso raro pero posible)
        if not chunks and player.playing:
            chunks = [[]]

        for i, chunk in enumerate(chunks):
            desc = ""
            if player.playing:
                desc += lang_service.get_text("music_queue_current", lang, title=player.current.title) + "\n\n"
            
            if chunk:
                desc += lang_service.get_text("music_queue_next", lang) + "\n"
                for j, track in enumerate(chunk):
                    idx = (i * chunk_size) + j + 1
                    desc += f"`{idx}.` {track.title} - *{track.author}*\n"
            
            embed = discord.Embed(title=lang_service.get_text("music_queue_title", lang), description=desc, color=settings.COLORS["INFO"])
            embed.set_footer(text=lang_service.get_text("music_queue_footer", lang, current=i+1, total=len(chunks), tracks=len(player.queue)))
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.send(embed=pages[0], view=view)

    @commands.hybrid_command(name="pause", description="Pausa o reanuda la música.")
    async def pause(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return
        if not ctx.voice_client or not ctx.voice_client.playing:
             return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
        
        player: wavelink.Player = ctx.voice_client
        new_state = not player.paused
        await player.pause(new_state)
        
        # Sincronizar estado visual del botón si existe
        if hasattr(player, "last_view") and player.last_view:
            for child in player.last_view.children:
                if isinstance(child, discord.ui.Button) and child.emoji == settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["PAUSE_RESUME"]:
                    child.style = discord.ButtonStyle.danger if new_state else discord.ButtonStyle.primary
                    break
            try:
                if player.last_msg: await player.last_msg.edit(view=player.last_view)
            except discord.HTTPException: pass

        msg = lang_service.get_text("music_paused" if new_state else "music_resumed", lang)
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), msg, lite=True))

    @commands.hybrid_command(name="shuffle", description="Mezcla aleatoriamente la cola de reproducción.")
    async def shuffle(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return
        if not ctx.voice_client or not ctx.voice_client.playing:
             return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
        
        player: wavelink.Player = ctx.voice_client
        if player.queue.is_empty:
             return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_shuffle", lang), lang_service.get_text("music_queue_empty", lang), lite=True), ephemeral=True)

        player.queue.shuffle()
        msg = lang_service.get_text("music_shuffled", lang)
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_shuffle", lang), msg, lite=True))

    @commands.hybrid_command(name="autoplay", description="Activa/Desactiva la reproducción automática recomendada.")
    async def autoplay(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return
        if not ctx.voice_client:
             return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
        
        player: wavelink.Player = ctx.voice_client
        
        # Toggle Smart Autoplay
        current = getattr(player, "smart_autoplay", False)
        player.smart_autoplay = not current
        player.autoplay = wavelink.AutoPlayMode.disabled # Forzamos nativo OFF
        
        if player.smart_autoplay:
            msg = lang_service.get_text("music_autoplay_on", lang)
        else:
            msg = lang_service.get_text("music_autoplay_off", lang)
            
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_autoplay", lang), msg, lite=True))

    @commands.hybrid_command(name="loop", description="Cambia el modo de repetición (Pista / Cola / Apagado).")
    async def loop(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return
        if not ctx.voice_client or not ctx.voice_client.playing:
             return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
        
        player: wavelink.Player = ctx.voice_client
        
        if player.queue.mode == wavelink.QueueMode.normal:
            player.queue.mode = wavelink.QueueMode.loop
            msg = lang_service.get_text("music_loop_track", lang)
        elif player.queue.mode == wavelink.QueueMode.loop:
            player.queue.mode = wavelink.QueueMode.loop_all
            msg = lang_service.get_text("music_loop_queue", lang)
        else:
            player.queue.mode = wavelink.QueueMode.normal
            msg = lang_service.get_text("music_loop_off", lang)
            
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_loop", lang), msg, lite=True))

    @commands.hybrid_command(name="volume", description="Ajusta el volumen (0-100).")
    @app_commands.describe(nivel="Nivel de volumen")
    async def volume(self, ctx: commands.Context, nivel: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return
        if not ctx.voice_client:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True, ephemeral=True))
            
        nivel = max(0, min(100, nivel))
        
        # Optimización: No hacer nada si el volumen ya es el deseado
        if ctx.voice_client.volume != nivel:
            await ctx.voice_client.set_volume(nivel)
        
        msg = lang_service.get_text("music_volume", lang, vol=nivel)
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_volume", lang), msg, lite=True))

    @commands.hybrid_command(name="nowlistening", aliases=["np"], description="Muestra la canción actual.")
    async def nowlistening(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not ctx.voice_client or not ctx.voice_client.playing or not ctx.voice_client.current:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True, ephemeral=True))
        
        track = ctx.voice_client.current
        player = ctx.voice_client
        embed = music_service.create_np_embed(player, track, lang)
        
        # Añadimos controles también al mensaje de /np para facilitar el uso
        view = music_service.MusicControls(player, author_id=None, lang=lang)
        await ctx.send(embed=embed, view=view)

    # --- EVENTOS ---

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        if not player: return

        # Registrar que la canción empezó a sonar (Feedback positivo inicial)
        await db_service.record_song_feedback(player.guild.id, payload.track.identifier, is_skip=False)

        if not hasattr(player, "home") or not player.home: return
        
        # Borrar mensaje anterior si existe para no hacer spam
        if hasattr(player, "last_msg") and player.last_msg:
            try: await player.last_msg.delete()
            except discord.HTTPException: pass
            
        # Detener vista anterior para liberar recursos y evitar interacciones en mensajes viejos
        if hasattr(player, "last_view") and player.last_view:
            player.last_view.stop()

        # --- CROSSFADE / FADE IN ---
        # Si está configurado, aplicamos un filtro de volumen para simular fade-in
        fade_duration = settings.MUSIC_CONFIG.get("CROSSFADE_DURATION", 0)
        if fade_duration > 0:
            self.bot.loop.create_task(music_service.fade_in(player, fade_duration))

        track = payload.track
        lang = await lang_service.get_guild_lang(player.guild.id)
        
        embed = music_service.create_np_embed(player, track, lang)
        
        # Usamos author_id=None para permitir que cualquiera en el canal use los botones
        # Esto soluciona el problema de que los botones no funcionaran al inicio
        view = music_service.MusicControls(player, author_id=None, lang=lang) 
        
        player.last_view = view # Guardamos referencia para detenerla luego
        try:
            player.last_msg = await player.home.send(embed=embed, view=view)
        except (discord.NotFound, discord.Forbidden, AttributeError):
            logger.warning(f"⚠️ No se pudo enviar mensaje de 'Now Playing' en {player.guild.name} (Canal inaccesible)")
            player.last_msg = None # Asegurar limpieza para evitar errores en stop/cleanup

    # Evento para reproducir siguiente canción automáticamente
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        logger.debug(f"🎵 [Music] TrackEnd: {payload.track.title} Reason: {payload.reason}")
        
        # Si el bot fue desconectado (ej. expulsado o manual), limpiamos y salimos
        if not player or not player.connected:
            if player: await music_service.cleanup_player(self.bot, player)
            return

        # Registrar si la canción fue saltada (Feedback negativo)
        if payload.reason == "replaced":
            await db_service.record_song_feedback(player.guild.id, payload.track.identifier, is_skip=True)
            return # <--- FIX: Si fue reemplazada (Fallback o Skip), no seguir con la cola automática

        # 1. Si Autoplay está activado, Wavelink gestiona TODO (Cola + Recomendaciones).
        # No intervenimos para evitar conflictos de doble reproducción.
        if player.autoplay == wavelink.AutoPlayMode.enabled:
            return

        # Verificar si hubo error en la pista anterior para evitar bucles infinitos
        had_error = getattr(player, "last_track_error", False)
        player.last_track_error = False

        # 2. Gestión Manual (Cuando Autoplay está OFF)
        # Soporte para Loop de Pista (Repetir la misma)
        if player.queue.mode == wavelink.QueueMode.loop and not had_error:
            await player.play(payload.track)
            return

        # Soporte para Loop de Cola (Mover al final)
        if player.queue.mode == wavelink.QueueMode.loop_all and not had_error:
            await player.queue.put_wait(payload.track)

        # Reproducir siguiente canción de la cola si existe
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
            return

        # 4. Smart Autoplay (Si la cola está vacía)
        if getattr(player, "smart_autoplay", False):
            try:
                # UX: Mostrar que está "pensando" la siguiente canción
                recommendation = None
                try:
                    async with player.home.typing():
                        recommendation = await self.recommender.get_recommendation(player)
                except Exception:
                    recommendation = await self.recommender.get_recommendation(player)

                if recommendation:
                    await player.play(recommendation)
                    return
            except Exception as e:
                err_msg = str(e) or "Unknown Node Error"
                logger.error(f"❌ Error en Autoplay Recomendación: {err_msg}")
                # Si falla, simplemente no reproduce nada y deja que el bot quede en silencio/idle
                if hasattr(player, "home") and player.home:
                    try:
                        await player.home.send(embed=embed_service.warning(lang_service.get_text("title_error", await lang_service.get_guild_lang(player.guild.id)), "⚠️ Autoplay error: No recommendations found.", lite=True))
                    except: pass

        # Si llegamos aquí, la cola terminó y no hay autoplay.
        # Deshabilitar botones del último mensaje para indicar fin de sesión.
        await music_service.cleanup_player(self.bot, player)
        
        # Desconectar automáticamente para ahorrar recursos (Protegido contra fallos de nodo)
        if player.connected:
            try:
                await player.disconnect()
            except Exception:
                # Si el nodo ya murió o devolvió 500, ignoramos el error de desconexión
                pass

            if hasattr(player, "home") and player.home:
                lang = await lang_service.get_guild_lang(player.guild.id)
                msg = lang_service.get_text("music_queue_empty", lang)
                try:
                    await player.home.send(embed=embed_service.info(lang_service.get_text("title_info", lang), f"{msg} 👋", lite=True))
                except discord.HTTPException: pass

async def setup(bot):
    await bot.add_cog(Music(bot))