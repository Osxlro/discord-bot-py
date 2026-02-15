import discord
import wavelink
import logging
import re
from discord import app_commands
from discord.ext import commands
from config import settings
from services.features import music_service
from services.core import lang_service
from services.utils import embed_service, pagination_service, voice_service

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
    @app_commands.describe(busqueda="Nombre de la canción o URL de Spotify/YouTube")
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

        # 1. Asegurar Player (Lógica delegada)
        player = await music_service.ensure_player(ctx, lang)
        if not player: return

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
                # Prioridad de búsqueda flexible basada en settings
                primary = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "spsearch")
                sources = [primary, "ytsearch", "scsearch"]
                sources = list(dict.fromkeys(sources)) # Eliminar duplicados
                
                last_err = None
                for source in sources:
                    try:
                        query = f"{source}:{busqueda}"
                        tracks = await wavelink.Playable.search(query)
                        if tracks:
                            logger.info(f"🔍 [Music] Búsqueda resuelta vía {source}")
                            break
                    except Exception as e:
                        last_err = e
                        continue
                
                # Si fallaron todos los intentos y hubo error, lo lanzamos
                if not tracks and last_err:
                    raise last_err

            if not tracks:
                return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_music", lang), lang_service.get_text("music_search_empty", lang, query=busqueda or "Unknown")))

            # 4. Reproducir o Encolar delegada al servicio
            await music_service.handle_enqueue(ctx, player, tracks, lang)
        
        except Exception as e:
            logger.exception("Error en comando play")
            msg = music_service.get_music_error_message(e, lang)
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg))

    @commands.hybrid_command(name="previous", description="Vuelve a la canción anterior o reinicia la actual.")
    async def previous(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return
        
        player: wavelink.Player = ctx.voice_client
        if not player.playing or not player.current:
             return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)

        if player.position > 10000:
            await player.seek(0)
            msg = lang_service.get_text("music_restarted", lang)
        else:
            history = player.queue.history
            if len(history) == 0:
                await player.seek(0)
                msg = lang_service.get_text("music_restarted", lang)
            else:
                prev_track = history.pop()
                
                current_track = player.current
                player.queue.put_at(0, current_track)
                
                await player.play(prev_track)
                msg = lang_service.get_text("music_previous", lang)
        
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_music", lang), msg, lite=True))

    @commands.hybrid_command(name="stop", description="Detiene la música y desconecta al bot.")
    async def stop(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return

        player = ctx.voice_client
        if player:
            # Limpiar interfaz antes de desconectar
            await music_service.cleanup_player(player)

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
        
        pages = music_service.get_queue_pages(player, lang)
        if not pages:
            msg = lang_service.get_text("music_error_nothing", lang)
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_queue", lang), msg, lite=True))

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
        
        await music_service.sync_ui(player)

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
        await music_service.sync_ui(player)
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
            
        await music_service.sync_ui(player)
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
            
        await music_service.sync_ui(player)
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