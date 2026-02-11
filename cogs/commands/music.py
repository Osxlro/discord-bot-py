import discord
import asyncio
import wavelink
import logging
import random
import re
from discord import app_commands
from discord.ext import commands, tasks
from config import settings
from services import embed_service, lang_service, pagination_service, algorithm_service, db_service, music_service, voice_service

logger = logging.getLogger(__name__)

URL_RX = re.compile(r'https?://(?:www\.)?.+')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Conecta a Lavalink al cargar el Cog."""
        self.bot.loop.create_task(music_service.connect_nodes(self.bot))

    async def cog_unload(self):
        pass

    async def play_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await music_service.get_search_choices(current)

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
            await music_service.connect_nodes(self.bot)
            
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
                    voice_service.voice_targets[ctx.guild.id] = ctx.author.voice.channel.id
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

async def setup(bot):
    await bot.add_cog(Music(bot))