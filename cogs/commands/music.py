import discord
import wavelink
import logging
import random
import re
from discord import app_commands
from discord.ext import commands
from config import settings
from services import embed_service, lang_service, pagination_service, algorithm_service

logger = logging.getLogger(__name__)

class MusicControls(discord.ui.View):
    """Botones interactivos para controlar la música."""
    def __init__(self, player: wavelink.Player, author_id: int = None, lang: str = "es"):
        super().__init__(timeout=None)
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

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.paused:
            await self.player.pause(False)
            msg = lang_service.get_text("music_resumed", self.lang)
        else:
            await self.player.pause(True)
            msg = lang_service.get_text("music_paused", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.skip(force=True)
        msg = lang_service.get_text("music_skipped", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.disconnect()
        msg = lang_service.get_text("music_stopped", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)
        self.stop() # Detiene la vista

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.queue.shuffle()
        msg = lang_service.get_text("music_shuffled", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ciclo: Normal -> Track -> Queue -> Normal
        if self.player.queue.mode == wavelink.QueueMode.normal:
            self.player.queue.mode = wavelink.QueueMode.loop
            msg = lang_service.get_text("music_loop_track", self.lang)
            button.emoji = "🔂"
            button.style = discord.ButtonStyle.success
        elif self.player.queue.mode == wavelink.QueueMode.loop:
            self.player.queue.mode = wavelink.QueueMode.loop_all
            msg = lang_service.get_text("music_loop_queue", self.lang)
            button.emoji = "🔁"
            button.style = discord.ButtonStyle.success
        else:
            self.player.queue.mode = wavelink.QueueMode.normal
            msg = lang_service.get_text("music_loop_off", self.lang)
            button.emoji = "🔁"
            button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(emoji="♾️", style=discord.ButtonStyle.secondary, row=1)
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

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=1)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_vol = max(self.player.volume - 10, 0)
        await self.player.set_volume(new_vol)
        await interaction.response.send_message(f"🔉 {new_vol}%", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_vol = min(self.player.volume + 10, 100)
        await self.player.set_volume(new_vol)
        await interaction.response.send_message(f"🔊 {new_vol}%", ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recommender = algorithm_service.RecommendationEngine()

    async def cog_load(self):
        """Conecta a Lavalink al cargar el Cog."""
        # Usamos create_task para no bloquear el arranque del bot si Lavalink está caído
        self.bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Intenta conectar a Lavalink en segundo plano."""
        await self.bot.wait_until_ready()
        
        if not wavelink.Pool.nodes:
            try:
                node_config = settings.LAVALINK_CONFIG
                protocol = "https" if node_config.get("SECURE") else "http"
                nodes = [
                    wavelink.Node(
                        uri=f"{protocol}://{node_config['HOST']}:{node_config['PORT']}",
                        password=node_config['PASSWORD']
                    )
                ]
                await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
                logger.info("🔗 [Music] Conectando a nodos Lavalink...")
            except Exception as e:
                logger.error(f"❌ [Music] No se pudo conectar a Lavalink: {e}")
                logger.warning("⚠️ El bot inició, pero la música no funcionará hasta que Lavalink esté online.")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"✅ [Music] Nodo Lavalink conectado: {payload.node.identifier}")

    async def play_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        if not current:
            return []
        try:
            # Búsqueda rápida en YouTube para autocompletado
            tracks = await wavelink.Playable.search(f"ytsearch:{current}")
            choices = []
            for track in tracks[:10]:
                seconds = track.length // 1000
                if track.is_stream:
                    duration = "LIVE" # Se usará texto localizado en display, aquí es solo para autocomplete
                else:
                    duration = f"{seconds // 60}:{seconds % 60:02}"
                name = f"[{duration}] {track.title[:65]} - {track.author[:15]}"
                choices.append(app_commands.Choice(name=name, value=track.uri or track.title))
            return choices
        except Exception:
            return []

    @commands.hybrid_command(name="play", description="Reproduce música desde YouTube, SoundCloud, etc.")
    @app_commands.describe(busqueda="Nombre de la canción o URL")
    @app_commands.autocomplete(busqueda=play_autocomplete)
    async def play(self, ctx: commands.Context, busqueda: str):
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

        # Guardamos el canal de texto para enviar mensajes de "Now Playing"
        player.home = ctx.channel

        # 3. Buscar canción
        await ctx.defer()
        
        # Auto-selección de proveedor (YouTube por defecto si no es URL)
        url_rx = re.compile(r'https?://(?:www\.)?.+')
        search_query = busqueda
        if not url_rx.match(busqueda):
            provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "yt")
            if provider == "yt": search_query = f"ytsearch:{busqueda}"
            elif provider == "sc": search_query = f"scsearch:{busqueda}"
            elif provider == "sp": search_query = f"spsearch:{busqueda}"

        tracks = await wavelink.Playable.search(search_query)
        if not tracks:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_music", lang), lang_service.get_text("music_search_empty", lang, query=busqueda)))

        # 4. Reproducir o Encolar (Soporte Playlist)
        if isinstance(tracks, wavelink.Playlist):
            # Es una Playlist
            for track in tracks:
                await player.queue.put_wait(track)
            
            msg = lang_service.get_text("music_playlist_added", lang, name=tracks.name, count=len(tracks))
            await ctx.send(embed=embed_service.success(lang_service.get_text("title_queue", lang), msg, lite=True))
            
            # Si no suena nada, reproducir la primera
            if not player.playing:
                await player.play(player.queue.get())
                
        else:
            # Es una búsqueda (Search), tomamos el primero
            track = tracks[0]
            
            if not player.playing:
                await player.play(track)
            else:
                await player.queue.put_wait(track)
                msg = lang_service.get_text("music_track_enqueued", lang, title=track.title)
                await ctx.send(embed=embed_service.success(lang_service.get_text("title_queue", lang), msg, lite=True))

    @commands.hybrid_command(name="stop", description="Detiene la música y desconecta al bot.")
    async def stop(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if ctx.voice_client:
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
        chunk_size = 10
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
            await ctx.send(embed=pages[0], view=view)

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
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang)))
            
        nivel = max(0, min(100, nivel))
        await ctx.voice_client.set_volume(nivel)
        
        msg = lang_service.get_text("music_volume", lang, vol=nivel)
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_volume", lang), msg, lite=True))

    @commands.hybrid_command(name="nowlistening", aliases=["np"], description="Muestra la canción actual.")
    async def nowlistening(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not ctx.voice_client or not ctx.voice_client.playing:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True))
        
        track = ctx.voice_client.current
        player = ctx.voice_client
        
        # Barra de progreso
        position = player.position
        length = track.length
        
        if track.is_stream:
            pos_str = lang_service.get_text("music_live", lang)
            len_str = "∞"
            bar = "▬" * 15 + "🔘"
        else:
            total_blocks = 15
            progress = int((position / length) * total_blocks) if length > 0 else 0
            bar = "▬" * progress + "🔘" + "▬" * (total_blocks - progress)
            pos_str = f"{int(position // 1000 // 60)}:{int(position // 1000 % 60):02}"
            len_str = f"{int(length // 1000 // 60)}:{int(length // 1000 % 60):02}"

        embed = discord.Embed(
            title=lang_service.get_text("music_now_listening", lang),
            description=f"[{track.title}]({track.uri})\n\n`{pos_str}` [{bar}] `{len_str}`",
            color=settings.COLORS["XP"]
        )
        if track.artwork: embed.set_thumbnail(url=track.artwork)
        embed.add_field(name=lang_service.get_text("music_field_author", lang), value=track.author, inline=True)
        
        await ctx.send(embed=embed)

    # --- EVENTOS ---

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        if not hasattr(player, "home") or not player.home: return
        
        # Borrar mensaje anterior si existe para no hacer spam
        if hasattr(player, "last_msg") and player.last_msg:
            try: await player.last_msg.delete()
            except: pass

        track = payload.track
        lang = await lang_service.get_guild_lang(player.guild.id)
        
        # Duración formateada
        if track.is_stream:
            duration_str = lang_service.get_text("music_live", lang)
        else:
            seconds = track.length // 1000
            duration_str = f"{seconds // 60}:{seconds % 60:02}"

        embed = discord.Embed(
            title=lang_service.get_text("music_now_playing_title", lang),
            description=f"{track.title}",
            color=settings.COLORS["XP"]
        )
        if track.artwork: embed.set_thumbnail(url=track.artwork)
        embed.add_field(name=lang_service.get_text("music_field_author", lang), value=track.author, inline=True)
        embed.add_field(name=lang_service.get_text("music_field_duration", lang), value=duration_str, inline=True)
        
        # Usamos author_id=None para permitir que cualquiera en el canal use los botones
        # Esto soluciona el problema de que los botones no funcionaran al inicio
        view = MusicControls(player, author_id=None, lang=lang) 

        player.last_msg = await player.home.send(embed=embed, view=view)

    # Evento para reproducir siguiente canción automáticamente
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        
        # Evitamos errores si el bot fue desconectado
        if not player.guild.voice_client:
            return

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