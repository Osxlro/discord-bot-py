import discord
import asyncio
import wavelink
import logging
import re
from discord import app_commands
from config import settings
from services import lang_service, embed_service, lyrics_service, voice_service

logger = logging.getLogger(__name__)

_is_connecting = False

# =============================================================================
# LÓGICA DE INTERFAZ (VISTAS Y BOTONES)
# =============================================================================

class MusicControls(discord.ui.View):
    """Botones interactivos para controlar la música."""
    def __init__(self, player: wavelink.Player, author_id: int = None, lang: str = "es"):
        super().__init__(timeout=settings.MUSIC_CONFIG["CONTROLS_TIMEOUT"])
        self.player = player
        self.author_id = author_id
        self.lang = lang
        self._sync_state()

    def _sync_state(self):
        """Sincroniza el estado visual de los botones con el estado interno del player."""
        for child in self.children:
            if not isinstance(child, discord.ui.Button): continue
            
            # Sincronizar Pausa
            if str(child.emoji) == settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["PAUSE_RESUME"]:
                child.style = discord.ButtonStyle.danger if self.player.paused else discord.ButtonStyle.primary
            
            # Sincronizar Autoplay
            elif str(child.emoji) == settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["AUTOPLAY"]:
                if getattr(self.player, "smart_autoplay", False):
                    child.style = discord.ButtonStyle.success
                else:
                    child.style = discord.ButtonStyle.secondary
            
            # Sincronizar Loop
            elif str(child.emoji) in settings.MUSIC_CONFIG["LOOP_EMOJIS"].values():
                mode = self.player.queue.mode
                if mode == wavelink.QueueMode.loop:
                    child.emoji = settings.MUSIC_CONFIG["LOOP_EMOJIS"]["TRACK"]
                    child.style = discord.ButtonStyle.success
                elif mode == wavelink.QueueMode.loop_all:
                    child.emoji = settings.MUSIC_CONFIG["LOOP_EMOJIS"]["QUEUE"]
                    child.style = discord.ButtonStyle.success
                # Normal es el default, no hace falta else

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.player.connected:
             await interaction.response.send_message(lang_service.get_text("music_error_nothing", self.lang), ephemeral=True)
             return False

        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message(lang_service.get_text("music_control_owner_error", self.lang), ephemeral=True)
            return False
        
        if not interaction.user.voice or (self.player.channel and interaction.user.voice.channel.id != self.player.channel.id):
             await interaction.response.send_message(lang_service.get_text("music_control_voice_error", self.lang), ephemeral=True)
             return False

        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if hasattr(self.player, "last_msg") and self.player.last_msg:
                await self.player.last_msg.edit(view=self)
        except discord.HTTPException:
            pass # El mensaje pudo haber sido borrado

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["PAUSE_RESUME"], style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_state = not self.player.paused
        await self.player.pause(new_state)
        button.style = discord.ButtonStyle.danger if new_state else discord.ButtonStyle.primary
        msg_key = "music_paused" if new_state else "music_resumed"
        try: await interaction.response.edit_message(view=self)
        except discord.HTTPException: pass
        await interaction.followup.send(lang_service.get_text(msg_key, self.lang), ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["SKIP"], style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Prevención de spam/errores si ya se detuvo
        if not self.player.playing or not self.player.current:
             return await interaction.response.send_message(lang_service.get_text("music_error_nothing", self.lang), ephemeral=True)

        await self.player.skip(force=True)
        msg = lang_service.get_text("music_skipped", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["STOP"], style=discord.ButtonStyle.danger, row=0)
    async def stop_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Actualizar UI primero para respuesta rápida
        for child in self.children:
            child.disabled = True
        self.stop()
        msg = lang_service.get_text("music_stopped", self.lang)
        try:
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(msg, ephemeral=True)
        except discord.HTTPException:
            pass

        # 2. Usar helper de limpieza (evita duplicar lógica)
        await cleanup_player(self.player.client, self.player, skip_message_edit=True)

        # 3. Desconectar
        if self.player.connected:
            await self.player.disconnect()

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["SHUFFLE"], style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.queue.shuffle()
        msg = lang_service.get_text("music_shuffled", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["LOOP_EMOJIS"]["OFF"], style=discord.ButtonStyle.secondary, row=1)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        
        try: await interaction.response.edit_message(view=self)
        except discord.HTTPException: pass
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(emoji=settings.MUSIC_CONFIG["BUTTON_EMOJIS"]["AUTOPLAY"], style=discord.ButtonStyle.secondary, row=1)
    async def autoplay(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = getattr(self.player, "smart_autoplay", False)
        self.player.smart_autoplay = not current
        self.player.autoplay = wavelink.AutoPlayMode.disabled
        
        if self.player.smart_autoplay:
            msg = lang_service.get_text("music_autoplay_on", self.lang)
            button.style = discord.ButtonStyle.success
        else:
            msg = lang_service.get_text("music_autoplay_off", self.lang)
            button.style = discord.ButtonStyle.secondary
        
        try: await interaction.response.edit_message(view=self)
        except discord.HTTPException: pass
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
        if not track or not track.title or track.is_stream:
            return await interaction.followup.send(lang_service.get_text("music_error_nothing", self.lang), ephemeral=True)
        
        # Mejora: Limpiar el título de "Official Video", "Lyrics", etc. para una búsqueda más precisa
        clean_title = re.sub(r"[\(\[].*?[\)\]]", "", track.title).strip()
        
        # Intentar búsqueda con título limpio y autor
        lyrics = await lyrics_service.get_lyrics(clean_title, track.author)
        
        # Fallback: Si falla, intentar solo con el título limpio (útil si el autor en YT es raro)
        if not lyrics:
            lyrics = await lyrics_service.get_lyrics(clean_title, "")

        if lyrics:
            embed = discord.Embed(title=lang_service.get_text("music_lyrics_title", self.lang, title=track.title), description=lyrics[:4096], color=settings.COLORS["INFO"])
            if len(lyrics) > 4096:
                embed.set_footer(text="Letra truncada.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(lang_service.get_text("music_lyrics_not_found", self.lang), ephemeral=True)

# =============================================================================
# FUNCIONES AUXILIARES (HELPERS)
# =============================================================================

async def cleanup_player(bot, player: wavelink.Player, skip_message_edit: bool = False):
    """Realiza limpieza de interfaz y persistencia al detener el player."""
    if not player: return

    # 1. Limpiar persistencia de Voice
    voice_service.voice_targets.pop(player.guild.id, None)

    # 2. Deshabilitar botones visualmente
    if hasattr(player, "last_view") and player.last_view:
        for child in player.last_view.children:
            child.disabled = True
        if not skip_message_edit:
            try:
                if player.last_msg: await player.last_msg.edit(view=player.last_view)
            except discord.HTTPException: pass
        player.last_view.stop()
    
    # Limpiar referencias
    player.last_view = None
    player.last_msg = None
    player.home = None # Liberar referencia al canal de texto
    
    # Limpiar cola
    if hasattr(player, "queue"):
        try: player.queue.clear()
        except: pass
        
    # Resetear estados internos
    player.smart_autoplay = False
    player.last_track_error = False

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

            logger.info(f"🔄 [Music Service] Intento de conexión {i+1}/{max_retries}...")

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
        # Intentar autocompletado siguiendo el orden: Spotify -> YouTube -> SoundCloud
        sources = ["spsearch", "ytsearch", "scsearch"]
        tracks = []
        
        for source in sources:
            try:
                tracks = await wavelink.Playable.search(f"{source}:{current}")
                if tracks:
                    break
            except:
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

def format_duration(milliseconds: int) -> str:
    """Formatea milisegundos a MM:SS o HH:MM:SS."""
    seconds = milliseconds // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"

def create_np_embed(player: wavelink.Player, track: wavelink.Playable, lang: str) -> discord.Embed:
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
        if length > 0:
            progress = int((position / length) * total_blocks)
        else:
            progress = 0
            
        progress = min(progress, total_blocks) # Asegurar que no exceda el límite visual
        bar = settings.MUSIC_CONFIG["PROGRESS_BAR_CHAR"] * progress + settings.MUSIC_CONFIG["PROGRESS_BAR_POINTER"] + settings.MUSIC_CONFIG["PROGRESS_BAR_CHAR"] * (total_blocks - progress)
        pos_str = format_duration(position)
        len_str = format_duration(length)

    desc = lang_service.get_text("music_np_desc", lang, title=track.title, uri=track.uri or "", pos=pos_str, bar=bar, len=len_str)

    # Detectar la fuente para el icono
    source = getattr(track, 'source', '').lower()
    uri = (track.uri or "").lower()
    
    if "youtube" in source or "youtube" in uri or "youtu.be" in uri:
        icon = settings.MUSIC_CONFIG["SOURCE_EMOJIS"]["youtube"]
    elif "spotify" in source or "spotify" in uri:
        icon = settings.MUSIC_CONFIG["SOURCE_EMOJIS"]["spotify"]
    elif "soundcloud" in source or "soundcloud" in uri:
        icon = settings.MUSIC_CONFIG["SOURCE_EMOJIS"]["soundcloud"]
    else:
        icon = settings.MUSIC_CONFIG["SOURCE_EMOJIS"]["unknown"]

    embed = discord.Embed(
        title=f"{icon} {lang_service.get_text('music_now_playing_title', lang)}",
        description=desc,
        color=settings.COLORS["INFO"]
    )
    if track.artwork: embed.set_thumbnail(url=track.artwork)
    
    # Mostrar quién solicitó la canción
    if hasattr(track, "requester") and track.requester:
        embed.set_footer(text=lang_service.get_text("music_requested_by", lang, user=track.requester.display_name), icon_url=track.requester.display_avatar.url)
        
    embed.add_field(name=lang_service.get_text("music_field_author", lang), value=track.author, inline=True)

    # Álbum y Año (Soporte para metadatos extendidos de Spotify/Plugins)
    album = getattr(track, "album", None)
    if album:
        album_name = getattr(album, "name", str(album))
        embed.add_field(name=lang_service.get_text("music_field_album", lang), value=album_name, inline=True)

    # Intentar obtener el año desde atributos dinámicos (LavaSrc)
    year = getattr(track, 'year', None)
    if year:
        embed.add_field(name=lang_service.get_text("music_field_year", lang), value=str(year), inline=True)

    return embed
