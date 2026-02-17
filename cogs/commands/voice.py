import logging
from discord.ext import commands
from services.core import lang_service
from services.utils import voice_service

logger = logging.getLogger(__name__)

class Voice(commands.Cog):
    """
    Cog encargado de la gestión de conexiones de voz.
    Permite al bot unirse o salir de canales de voz, manteniendo un estado
    de persistencia para reconexiones automáticas.
    """
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        """Limpia las conexiones de voz al descargar el cog."""
        for guild_id in list(voice_service.voice_targets.keys()):
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client:
                self.bot.loop.create_task(guild.voice_client.disconnect(force=True))
        voice_service.voice_targets.clear()

    @commands.hybrid_command(name="join", description="Conecta el bot a tu canal de voz (Modo Chill).")
    async def join(self, ctx: commands.Context):
        """Conecta al bot al canal de voz donde se encuentra el autor del comando."""
        # Obtener el idioma configurado para el servidor
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Delegar la lógica de conexión y validación de permisos al servicio
        embed, error_embed = await voice_service.handle_join(ctx.guild, ctx.author, lang)
        
        if error_embed:
            # Si hubo un error (ej: usuario no está en voz), enviar embed de error
            return await ctx.send(embed=error_embed)
            
        # Enviar confirmación de conexión exitosa
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="leave", description="Desconecta al bot del canal de voz.")
    async def leave(self, ctx: commands.Context):
        """Desconecta al bot del canal de voz actual en el servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Delegar la desconexión al servicio
        embed, _ = await voice_service.handle_leave(ctx.guild, lang)
        
        if embed:
            # Enviar confirmación de salida
            await ctx.send(embed=embed)
        else:
            # Si no estaba conectado, reaccionar con una duda
            try: await ctx.message.add_reaction("❓")
            except: pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Listener que detecta cambios en el estado de voz.
        Se usa principalmente para manejar reconexiones automáticas si el bot es desconectado.
        """
        await voice_service.handle_voice_state_update(self.bot, member, before, after)

async def setup(bot):
    """Función de entrada para cargar el Cog en el bot."""
    await bot.add_cog(Voice(bot))