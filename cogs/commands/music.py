import discord
import asyncio
import wavelink
import logging
import random
import re
from discord import app_commands
from discord.ext import commands
from config import settings
from services import embed_service, lang_service, pagination_service, algorithm_service, db_service, lyrics_service

logger = logging.getLogger(__name__)

class MusicControls(discord.ui.View):
    """Botones interactivos para controlar la música."""
    def __init__(self, player: wavelink.Player, author_id: int = None, lang: str = "es"):
        super().__init__(timeout=settings.MUSIC_CONFIG["CONTROLS_TIMEOUT"])
        self.player = player
        self.author_id = author_id
        self.lang = lang

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Si se definió un autor específico (modo estricto)
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message(lang_service.get_text("music_control_owner_error", self.lang), ephemeral=True)
            return False
        
        # Si es modo público (author_id=None), validar que esté en el mismo canal de voz
        if not interaction.user.voice or (self.player.channel and interaction.user.voice.channel != self.player.channel):
             await interaction.response.send_message(lang_service.get_text("music_control_voice_error", self.lang), ephemeral=True)
             return False

        return True

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["PAUSE_RESUME"], style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.paused:
            await self.player.pause(False)
            msg = lang_service.get_text("music_resumed", self.lang)
        else:
            await self.player.pause(True)
            msg = lang_service.get_text("music_paused", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["SKIP"], style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.skip(force=True)
        msg = lang_service.get_text("music_skipped", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["STOP"], style=discord.ButtonStyle.danger, row=0)
    async def stop_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.disconnect()
        
        # Fix: Limpiar persistencia de Voice si existe para evitar auto-reconexión
        voice_cog = self.player.client.get_cog("Voice")
        if voice_cog and hasattr(voice_cog, 'voice_targets'):
            voice_cog.voice_targets.pop(self.player.guild.id, None)
            
        msg = lang_service.get_text("music_stopped", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)
        self.stop() # Detiene la vista (View.stop)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["SHUFFLE"], style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.queue.shuffle()
        msg = lang_service.get_text("music_shuffled", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["LOOP_EMOJIS"]["OFF"], style=discord.ButtonStyle.secondary, row=1)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ciclo: Normal -> Track -> Queue -> Normal
        if self.player.queue.mode == wavelink.QueueMode.normal:
            self.player.queue.mode = wavelink.QueueMode.loop
            msg = lang_service.get_text("music_loop_track", self.lang)
            button.emoji = settings.MUSIC_CONFIG["LOOP_EMOJIS"]["TRACK"]
            button.style = discord.ButtonStyle.success
        elif self.player.queue.mode == wavelink.QueueMode.loop:
            self.player.queue.mode = wavelink.QueueMode.loop_all
            msg = lang_service.get_text("music_loop_queue", self.lang)
            button.emoji = settings.MUSIC_CONFIG["LOOP_EMOJIS"]["QUEUE"]
            button.style = discord.ButtonStyle.success
        else:
            self.player.queue.mode = wavelink.QueueMode.normal
            msg = lang_service.get_text("music_loop_off", self.lang)
            button.emoji = settings.MUSIC_CONFIG["LOOP_EMOJIS"]["OFF"]
            button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["AUTOPLAY"], style=discord.ButtonStyle.secondary, row=1)
    async def autoplay(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Toggle Smart Autoplay
        current = getattr(self.player, "smart_autoplay", False)
        self.player.smart_autoplay = not current
        self.player.autoplay = wavelink.AutoPlayMode.disabled # Forzamos nativo OFF para usar el nuestro
        
        if self.player.smart_autoplay:
            msg = lang_service.get_text("music_autoplay_on", self.lang)
            button.style = discord.ButtonStyle.success
        else:
            msg = lang_service.get_text("music_autoplay_off", self.lang)
            button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["VOL_DOWN"], style=discord.ButtonStyle.secondary, row=1)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_vol = max(self.player.volume - settings.MUSIC_CONFIG["VOLUME_STEP"], 0)
        await self.player.set_volume(new_vol)
        await interaction.response.send_message(lang_service.get_text("music_vol_changed", self.lang, vol=new_vol), ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["VOL_UP"], style=discord.ButtonStyle.secondary, row=1)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_vol = min(self.player.volume + settings.MUSIC_CONFIG["VOLUME_STEP"], 100)
        await self.player.set_volume(new_vol)
        await interaction.response.send_message(lang_service.get_text("music_vol_changed", self.lang, vol=new_vol), ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["LYRICS"], style=discord.ButtonStyle.secondary, row=1)
    async def lyrics(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        track = self.player.current
        if not track:
            return await interaction.followup.send(lang_service.get_text("music_error_nothing", self.lang), ephemeral=True)
        
        lyrics = await lyrics_service.get_lyrics(track.title, track.author)
        if lyrics:
            embed = discord.Embed(title=lang_service.get_text("music_lyrics_title", self.lang, title=track.title), description=lyrics[:4096], color=settings.COLORS["INFO"])
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(lang_service.get_text("music_lyrics_not_found", self.lang), ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recommender = algorithm_service.RecommendationEngine()
        self.node_configs = []
        self._is_connecting = False

    async def _fade_in(self, player: wavelink.Player, duration_ms: int):
        """Simula un efecto de Fade-In ajustando el volumen gradualmente."""
        # Objetivo: Volumen actual configurado o el default
        target_vol = player.volume
        
        # Si el volumen es 0, no hay nada que hacer (ahorra recursos)
        if target_vol == 0:
            return

        last_set_vol = 0 # Para detectar cambios manuales
        current_track = player.current # Guardamos referencia para verificar cambios
        
        # Inicio: Volumen 0
        await player.set_volume(0)
        
        # Animación
        steps = settings.MUSIC_CONFIG["FADE_IN_STEPS"]
        step_delay = (duration_ms / 1000) / steps
        vol_step = target_vol / steps
        
        for i in range(1, steps + 1):
            # Si la canción cambió o se detuvo, cancelamos el fade para no afectar la siguiente
            if not player.playing or player.current != current_track:
                return

            # Si el volumen cambió externamente (ej: usuario usó /volume), cancelamos el fade
            # Usamos un margen de error de 1 por posibles redondeos
            if last_set_vol > 0 and abs(player.volume - last_set_vol) > settings.MUSIC_CONFIG["VOLUME_TOLERANCE"]:
                return

            await asyncio.sleep(step_delay)
            new_vol = int(vol_step * i)
            await player.set_volume(new_vol)
            last_set_vol = new_vol
        
        # Asegurar volumen final exacto
        await player.set_volume(target_vol)

    def _create_np_embed(self, player: wavelink.Player, track: wavelink.Playable, lang: str) -> discord.Embed:
        """Genera el embed de 'Reproduciendo Ahora' con barra de progreso."""
        position = player.position
        length = track.length
        
        if track.is_stream:
            pos_str = lang_service.get_text("music_live", lang)
            len_str = "∞"
            bar_len = settings.MUSIC_CONFIG["STREAM_BAR_LENGTH"]
            bar = settings.MUSIC_CONFIG["PROGRESS_BAR_CHAR"] * bar_len + settings.MUSIC_CONFIG["PROGRESS_BAR_POINTER"]
        else:
            total_blocks = settings.MUSIC_CONFIG["PROGRESS_BAR_LENGTH"]
            progress = int((position / length) * total_blocks) if length > 0 else 0
            bar = settings.MUSIC_CONFIG["PROGRESS_BAR_CHAR"] * progress + settings.MUSIC_CONFIG["PROGRESS_BAR_POINTER"] + settings.MUSIC_CONFIG["PROGRESS_BAR_CHAR"] * (total_blocks - progress)
            pos_str = f"{int(position // 1000 // 60)}:{int(position // 1000 % 60):02}"
            len_str = f"{int(length // 1000 // 60)}:{int(length // 1000 % 60):02}"

        desc = lang_service.get_text("music_np_desc", lang, title=track.title, uri=track.uri, pos=pos_str, bar=bar, len=len_str)

        embed = discord.Embed(
            title=lang_service.get_text("music_now_playing_title", lang),
            description=desc,
            color=settings.COLORS["INFO"]
        )
        if track.artwork: embed.set_thumbnail(url=track.artwork)
        embed.add_field(name=lang_service.get_text("music_field_author", lang), value=track.author, inline=True)
        return embed

    async def cog_load(self):
        """Conecta a Lavalink al cargar el Cog."""
        # Usamos create_task para no bloquear el arranque del bot si Lavalink está caído
        self.bot.loop.create_task(self.connect_nodes())

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

    async def connect_best_node(self):
        """Itera sobre los nodos configurados hasta conectar uno."""
        if self._is_connecting or not self.node_configs:
            return
        
        self._is_connecting = True
        try:
            while True:
                # Si ya hay un nodo conectado, terminamos
                if wavelink.Pool.nodes:
                    for node in wavelink.Pool.nodes.values():
                        if node.status == wavelink.NodeStatus.CONNECTED:
                            return

                logger.info(f"🔄 [Music] Buscando mejor nodo disponible entre {len(self.node_configs)} opciones...")

                for _ in range(len(self.node_configs)):
                    # Rotación: Tomar primero, mover al final
                    config = self.node_configs.pop(0)
                    self.node_configs.append(config)
                    
                    identifier = config.get("IDENTIFIER", config["HOST"])
                    
                    # Limpieza preventiva de nodos zombies
                    existing = wavelink.Pool.get_node(identifier)
                    if existing:
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
                            def check(p): return p.node.identifier == identifier
                            await self.bot.wait_for('wavelink_node_ready', check=check, timeout=10.0)
                            return # Éxito, salimos del bucle
                        except asyncio.TimeoutError:
                            logger.warning(f"⚠️ [Music] Nodo {identifier} no respondió. Probando siguiente...")
                            node = wavelink.Pool.get_node(identifier)
                            if node: await node.close() # Matar reintentos
                            
                    except Exception as e:
                        logger.error(f"❌ [Music] Error nodo {identifier}: {e}")
                
                logger.error("❌ [Music] Todos los nodos fallaron. Reintentando en 30s...")
                await asyncio.sleep(30)
        finally:
            self._is_connecting = False

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"✅ [Music] Nodo Lavalink conectado: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_node_closed(self, payload: wavelink.NodeClosedEventPayload):
        """Detecta caída de nodo y activa Failover."""
        logger.warning(f"⚠️ [Music] Nodo {payload.node.identifier} desconectado. Iniciando Failover...")
        await asyncio.sleep(1)
        await self.connect_best_node()

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
            choices = []
            for track in tracks[:settings.MUSIC_CONFIG["AUTOCOMPLETE_LIMIT"]]:
                seconds = track.length // 1000
                if track.is_stream:
                    duration = "LIVE" # Se usará texto localizado en display, aquí es solo para autocomplete
                else:
                    duration = f"{seconds // 60}:{seconds % 60:02}"
                
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
        await ctx.defer()

        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # 1. Verificar canal de voz
        if not ctx.author.voice:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_join", lang)))

        # 2. Obtener o crear Player
        if not ctx.voice_client:
            try:
                # self_deaf=True para no escuchar a los usuarios (ahorra recursos)
                player: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
                await player.set_volume(settings.LAVALINK_CONFIG.get("DEFAULT_VOLUME", 50))
            except Exception as e:
                return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), str(e)))
        else:
            player: wavelink.Player = ctx.voice_client
            # Si el bot está muteado (por ejemplo, por /join de voice.py), lo desmuteamos
            if ctx.guild.me.voice.self_mute:
                await ctx.guild.me.edit(mute=False)
            
            # Si el usuario está en otro canal, movemos al bot
            if ctx.author.voice.channel.id != player.channel.id:
                await player.move_to(ctx.author.voice.channel)
                # Actualizar target de Voice cog si existe para evitar que intente devolverlo
                voice_cog = self.bot.get_cog("Voice")
                if voice_cog and hasattr(voice_cog, 'voice_targets') and ctx.guild.id in voice_cog.voice_targets:
                    voice_cog.voice_targets[ctx.guild.id] = ctx.author.voice.channel.id

        # Guardamos el canal de texto para enviar mensajes de "Now Playing"
        player.home = ctx.channel

        # 3. Lógica de Búsqueda (Con Fallback)
        url_rx = re.compile(r'https?://(?:www\.)?.+')
        is_url = url_rx.match(busqueda)
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
                        logger.warning(f"⚠️ Fallo búsqueda en {source} ('{busqueda}'): {e}")
                        continue
                
                # Si fallaron todos los intentos y hubo error, lo lanzamos
                if not tracks and last_err:
                    raise last_err

            if not tracks:
                return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_music", lang), lang_service.get_text("music_search_empty", lang, query=busqueda)))

            # 4. Reproducir o Encolar (Soporte Playlist)
            if isinstance(tracks, wavelink.Playlist):
                for track in tracks:
                    await player.queue.put_wait(track)
                
                msg = lang_service.get_text("music_playlist_added", lang, name=tracks.name, count=len(tracks))
                await ctx.send(embed=embed_service.success(lang_service.get_text("title_queue", lang), msg, lite=True))
                
                if not player.playing:
                    await player.play(player.queue.get())
            else:
                track = tracks[0]
                if not player.playing:
                    await player.play(track)
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
        if ctx.voice_client:
            # Fix conflicto con Voice Cog: Limpiamos la persistencia para evitar auto-reconexión
            voice_cog = self.bot.get_cog("Voice")
            if voice_cog and hasattr(voice_cog, 'voice_targets'):
                voice_cog.voice_targets.pop(ctx.guild.id, None)

            await ctx.voice_client.disconnect()
            msg = lang_service.get_text("music_stopped", lang)
            await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), msg, lite=True))
        else:
            msg = lang_service.get_text("music_error_nothing", lang)
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg, lite=True), ephemeral=True)

    @commands.hybrid_command(name="skip", description="Salta la canción actual.")
    async def skip(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if ctx.voice_client and ctx.voice_client.playing:
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
        
        if not player or not player.playing:
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
        if not ctx.voice_client or not ctx.voice_client.playing:
             return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
        
        player: wavelink.Player = ctx.voice_client
        await player.pause(not player.paused)
        
        msg = lang_service.get_text("music_paused" if player.paused else "music_resumed", lang)
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), msg, lite=True))

    @commands.hybrid_command(name="shuffle", description="Mezcla aleatoriamente la cola de reproducción.")
    async def shuffle(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
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
        if not ctx.voice_client:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True, ephemeral=True))
            
        nivel = max(0, min(100, nivel))
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
        embed = self._create_np_embed(player, track, lang)
        
        await ctx.send(embed=embed)

    # --- EVENTOS ---

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        # Registrar que la canción empezó a sonar (Feedback positivo inicial)
        await db_service.record_song_feedback(player.guild.id, payload.track.identifier, is_skip=False)

        if not hasattr(player, "home") or not player.home: return
        
        # Borrar mensaje anterior si existe para no hacer spam
        if hasattr(player, "last_msg") and player.last_msg:
            try: await player.last_msg.delete()
            except: pass
            
        # Detener vista anterior para liberar recursos y evitar interacciones en mensajes viejos
        if hasattr(player, "last_view") and player.last_view:
            player.last_view.stop()

        # --- CROSSFADE / FADE IN ---
        # Si está configurado, aplicamos un filtro de volumen para simular fade-in
        fade_duration = settings.MUSIC_CONFIG.get("CROSSFADE_DURATION", 0)
        if fade_duration > 0:
            self.bot.loop.create_task(self._fade_in(player, fade_duration))

        track = payload.track
        lang = await lang_service.get_guild_lang(player.guild.id)
        
        embed = self._create_np_embed(player, track, lang)
        
        # Usamos author_id=None para permitir que cualquiera en el canal use los botones
        # Esto soluciona el problema de que los botones no funcionaran al inicio
        view = MusicControls(player, author_id=None, lang=lang) 
        
        player.last_view = view # Guardamos referencia para detenerla luego
        player.last_msg = await player.home.send(embed=embed, view=view)

    # Evento para reproducir siguiente canción automáticamente
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        
        # Evitamos errores si el bot fue desconectado
        if not player or not player.guild or not player.guild.voice_client:
            return

        # Registrar si la canción fue saltada (Feedback negativo)
        if payload.reason == "replaced":
            await db_service.record_song_feedback(player.guild.id, payload.track.identifier, is_skip=True)

        # 1. Si Autoplay está activado, Wavelink gestiona TODO (Cola + Recomendaciones).
        # No intervenimos para evitar conflictos de doble reproducción.
        if player.autoplay == wavelink.AutoPlayMode.enabled:
            return

        # 2. Gestión Manual (Cuando Autoplay está OFF)
        # Soporte para Loop de Pista (Repetir la misma)
        if player.queue.mode == wavelink.QueueMode.loop:
            await player.play(payload.track)
            return

        # Soporte para Loop de Cola (Mover al final)
        if player.queue.mode == wavelink.QueueMode.loop_all:
            await player.queue.put_wait(payload.track)

        # Reproducir siguiente canción de la cola si existe
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
            return

        # 4. Smart Autoplay (Si la cola está vacía)
        if getattr(player, "smart_autoplay", False):
            recommendation = await self.recommender.get_recommendation(player)
            if recommendation:
                await player.play(recommendation)

async def setup(bot):
    await bot.add_cog(Music(bot))