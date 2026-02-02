import discord
import wavelink
import logging
from discord import app_commands
from discord.ext import commands
from config import settings
from services import embed_service, lang_service

logger = logging.getLogger(__name__)

class MusicControls(discord.ui.View):
    """Botones interactivos para controlar la música."""
    def __init__(self, player: wavelink.Player, author_id: int, lang: str):
        super().__init__(timeout=None)
        self.player = player
        self.author_id = author_id
        self.lang = lang

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ No puedes controlar esta sesión.", ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.paused:
            await self.player.pause(False)
            msg = lang_service.get_text("music_resumed", self.lang)
        else:
            await self.player.pause(True)
            msg = lang_service.get_text("music_paused", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.skip(force=True)
        msg = lang_service.get_text("music_skipped", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.player.disconnect()
        msg = lang_service.get_text("music_stopped", self.lang)
        await interaction.response.send_message(msg, ephemeral=True)
        self.stop() # Detiene la vista

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_vol = max(self.player.volume - 10, 0)
        await self.player.set_volume(new_vol)
        await interaction.response.send_message(f"🔉 {new_vol}%", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_vol = min(self.player.volume + 10, 100)
        await self.player.set_volume(new_vol)
        await interaction.response.send_message(f"🔊 {new_vol}%", ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Conecta a Lavalink al cargar el Cog."""
        if not wavelink.Pool.nodes:
            node_config = settings.LAVALINK_CONFIG
            nodes = [
                wavelink.Node(
                    uri=f"http://{node_config['HOST']}:{node_config['PORT']}",
                    password=node_config['PASSWORD']
                )
            ]
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            logger.info("🔗 [Music] Conectando a nodos Lavalink...")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"✅ [Music] Nodo Lavalink conectado: {payload.node.identifier}")

    @commands.hybrid_command(name="play", description="Reproduce música desde YouTube, SoundCloud, etc.")
    @app_commands.describe(busqueda="Nombre de la canción o URL")
    async def play(self, ctx: commands.Context, busqueda: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # 1. Verificar canal de voz
        if not ctx.author.voice:
            return await ctx.send(embed=embed_service.error("Error", lang_service.get_text("music_error_join", lang)))

        # 2. Obtener o crear Player
        if not ctx.voice_client:
            try:
                player: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                await player.set_volume(settings.LAVALINK_CONFIG.get("DEFAULT_VOLUME", 50))
            except Exception as e:
                return await ctx.send(embed=embed_service.error("Error", str(e)))
        else:
            player: wavelink.Player = ctx.voice_client

        # 3. Buscar canción
        await ctx.defer()
        
        # Auto-selección de proveedor (YouTube por defecto si no es URL)
        search_query = busqueda
        if not ("http" in busqueda or "www" in busqueda):
            provider = settings.LAVALINK_CONFIG.get("SEARCH_PROVIDER", "yt")
            if provider == "yt": search_query = f"ytsearch:{busqueda}"
            elif provider == "sc": search_query = f"scsearch:{busqueda}"

        tracks = await wavelink.Playable.search(search_query)
        if not tracks:
            return await ctx.send(embed=embed_service.warning("Music", lang_service.get_text("music_search_empty", lang, query=busqueda)))

        track = tracks[0]
        
        # 4. Reproducir o Encolar
        if not player.playing:
            await player.play(track)
            
            # Embed de "Now Playing"
            embed = discord.Embed(
                title=lang_service.get_text("music_playing", lang),
                description=f"[{track.title}]({track.uri})",
                color=settings.COLORS["XP"] # Usamos un color bonito
            )
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
            embed.add_field(name="👤 Autor", value=track.author, inline=True)
            embed.add_field(name="⏳ Duración", value=f"{track.length // 1000}s", inline=True)
            
            view = MusicControls(player, ctx.author.id, lang)
            await ctx.send(embed=embed, view=view)
        else:
            await player.queue.put_wait(track)
            msg = lang_service.get_text("music_track_enqueued", lang, title=track.title)
            await ctx.send(embed=embed_service.success("Cola", msg, lite=True))

    @commands.hybrid_command(name="stop", description="Detiene la música y desconecta al bot.")
    async def stop(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            msg = lang_service.get_text("music_stopped", lang)
            await ctx.send(embed=embed_service.success("Music", msg, lite=True))
        else:
            msg = lang_service.get_text("music_error_nothing", lang)
            await ctx.send(embed=embed_service.error("Error", msg, lite=True), ephemeral=True)

    @commands.hybrid_command(name="skip", description="Salta la canción actual.")
    async def skip(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if ctx.voice_client and ctx.voice_client.playing:
            await ctx.voice_client.skip(force=True)
            msg = lang_service.get_text("music_skipped", lang)
            await ctx.send(embed=embed_service.success("Music", msg, lite=True))
        else:
            msg = lang_service.get_text("music_error_nothing", lang)
            await ctx.send(embed=embed_service.error("Error", msg, lite=True), ephemeral=True)

    @commands.hybrid_command(name="queue", description="Muestra la cola de reproducción.")
    async def queue(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        player: wavelink.Player = ctx.voice_client
        
        if not player or (not player.playing and player.queue.is_empty):
            msg = lang_service.get_text("music_queue_empty", lang)
            return await ctx.send(embed=embed_service.info("Cola", msg, lite=True))

        desc = ""
        if player.playing:
            desc += f"**Actualmente:** [{player.current.title}]({player.current.uri})\n\n"
        
        if not player.queue.is_empty:
            desc += "**Próximas:**\n"
            for i, track in enumerate(player.queue[:10]): # Mostrar solo las primeras 10
                desc += f"`{i+1}.` {track.title} - *{track.author}*\n"
        
        embed = discord.Embed(title="📜 Cola de Música", description=desc, color=settings.COLORS["INFO"])
        if len(player.queue) > 10:
            embed.set_footer(text=f"Y {len(player.queue) - 10} más...")
            
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="volume", description="Ajusta el volumen (0-100).")
    @app_commands.describe(nivel="Nivel de volumen")
    async def volume(self, ctx: commands.Context, nivel: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if not ctx.voice_client:
            return await ctx.send(embed=embed_service.error("Error", lang_service.get_text("music_error_nothing", lang)))
            
        nivel = max(0, min(100, nivel))
        await ctx.voice_client.set_volume(nivel)
        
        msg = lang_service.get_text("music_volume", lang, vol=nivel)
        await ctx.send(embed=embed_service.success("Volumen", msg, lite=True))

    # Evento para reproducir siguiente canción automáticamente
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
            
            # Opcional: Enviar mensaje de "Now Playing" al canal donde se inició
            # Requiere guardar el ctx o channel_id en el player

async def setup(bot):
    await bot.add_cog(Music(bot))