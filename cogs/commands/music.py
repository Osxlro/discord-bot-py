import discord
import wavelink
import logging
import re
from discord import app_commands
from discord.ext import commands
from config import settings
from services.features import music_service
from services.integrations import lyrics_service
from services.core import lang_service
from services.utils import embed_service, pagination_service

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
        busqueda = busqueda.strip()
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id)

        if not busqueda:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_error", lang), lang_service.get_text("error_missing_args", lang)))

        # Verificación y conexión bajo demanda si los nodos están caídos
        if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
            await ctx.send(embed=embed_service.info(lang_service.get_text("title_info", lang), lang_service.get_text("music_connecting", lang), lite=True))
            await music_service.connect_nodes(self.bot)
            
            if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
                return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_err_lavalink_nodes", lang)))

        player = await music_service.ensure_player(ctx, lang)
        if not player: return

        player.home = ctx.channel

        try:
            tracks = await music_service.handle_play_search(busqueda)

            if not tracks:
                return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_music", lang), lang_service.get_text("music_search_empty", lang, query=busqueda or "Unknown")))

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
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
            
        nivel = max(0, min(100, nivel))
        
        # Optimización: No hacer nada si el volumen ya es el deseado
        if ctx.voice_client.volume != nivel:
            await ctx.voice_client.set_volume(nivel)
            if ctx.voice_client.current:
                await music_service.update_presence(self.bot, ctx.voice_client, ctx.voice_client.current, lang)
        
        msg = lang_service.get_text("music_volume", lang, vol=nivel)
        await ctx.send(embed=embed_service.success(lang_service.get_text("title_volume", lang), msg, lite=True))

    @commands.hybrid_command(name="nowlistening", aliases=["np"], description="Muestra la canción actual.")
    async def nowlistening(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not ctx.voice_client or not ctx.voice_client.playing or not ctx.voice_client.current:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
        
        track = ctx.voice_client.current
        player = ctx.voice_client
        embed = music_service.create_np_embed(player, track, lang)
        
        # Añadimos controles también al mensaje de /np para facilitar el uso
        view = music_service.MusicControls(player, author_id=None, lang=lang)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="lyrics", description="Busca la letra de la canción actual.")
    @app_commands.describe(busqueda="Opcional: Nombre de la canción o artista")
    async def lyrics(self, ctx: commands.Context, busqueda: str = None):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        await ctx.defer()

        title, artist = None, ""
        if busqueda:
            title = busqueda
        elif ctx.voice_client and ctx.voice_client.current:
            title = ctx.voice_client.current.title
            artist = ctx.voice_client.current.author
        else:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)

        # Mensaje temporal de búsqueda
        searching_msg = await ctx.send(embed=embed_service.info(lang_service.get_text("title_info", lang), f"🔍 {lang_service.get_text('music_lyrics_searching', lang)}...", lite=True))

        lyrics = await lyrics_service.get_lyrics(title, artist)
        await searching_msg.delete()

        if not lyrics:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_lyrics_not_found", lang), lite=True))

        # Dividir letras largas en páginas (Discord limit: 4096, usamos 2000 para seguridad y estética)
        pages = []
        lines = lyrics.split("\n")
        current_page = ""
        
        for line in lines:
            if len(current_page) + len(line) > 2000:
                pages.append(embed_service.info(lang_service.get_text("music_lyrics_title", lang, title=title), current_page))
                current_page = ""
            current_page += line + "\n"
        if current_page:
            pages.append(embed_service.info(lang_service.get_text("music_lyrics_title", lang, title=title), current_page))

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.send(embed=pages[0], view=view)

    @commands.hybrid_group(name="effect", description="Aplica filtros y efectos de audio a la música.")
    async def effect(self, ctx: commands.Context):
        """Grupo de comandos para gestionar efectos de audio."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @effect.command(name="apply", description="Activa un filtro de audio.")
    @app_commands.describe(nombre="El efecto a aplicar")
    @app_commands.choices(nombre=[
        app_commands.Choice(name="🔊 BassBoost (Bajos Potentes)", value="bassboost"),
        app_commands.Choice(name="💣 SuperBass (Extremo)", value="superbass"),
        app_commands.Choice(name="🌙 Nightcore (Rápido/Agudo)", value="nightcore"),
        app_commands.Choice(name="📼 Vaporwave (Lento/Grave)", value="vaporwave"),
        app_commands.Choice(name="🌀 8D Audio (Rotación)", value="8d"),
        app_commands.Choice(name="🎤 Karaoke (Sin voz)", value="karaoke"),
        app_commands.Choice(name="🎸 Metal", value="metal"),
        app_commands.Choice(name="🎹 Pop", value="pop"),
        app_commands.Choice(name="☁️ Soft (Suave)", value="soft"),
        app_commands.Choice(name="〰️ Tremolo", value="tremolo")
    ])
    async def effect_apply(self, ctx: commands.Context, nombre: app_commands.Choice[str]):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return

        await music_service.apply_filter(ctx.voice_client, nombre.value)
        await ctx.send(embed=embed_service.success(lang_service.get_text("music_effect_title", lang), lang_service.get_text("music_effect_applied", lang, filter=nombre.name), lite=True))

    @effect.command(name="disable", description="Desactiva todos los efectos de audio.")
    async def effect_disable(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not await music_service.check_voice(ctx): return

        await music_service.apply_filter(ctx.voice_client, "flat")
        await ctx.send(embed=embed_service.success(lang_service.get_text("music_effect_title", lang), lang_service.get_text("music_effect_cleared", lang), lite=True))

async def setup(bot):
    await bot.add_cog(Music(bot))