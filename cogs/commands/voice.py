import logging
from discord.ext import commands
from services.core import lang_service
from services.utils import voice_service

logger = logging.getLogger(__name__)

class Voice(commands.Cog):
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
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed, error_embed = await voice_service.handle_join(ctx.guild, ctx.author, lang)
        
        if error_embed:
            return await ctx.send(embed=error_embed)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="leave", description="Desconecta al bot del canal de voz.")
    async def leave(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed, _ = await voice_service.handle_leave(ctx.guild, lang)
        
        if embed:
            await ctx.send(embed=embed)
        else:
            try: await ctx.message.add_reaction("❓")
            except: pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Detecta desconexiones forzadas o inesperadas."""
        await voice_service.handle_voice_state_update(self.bot, member, before, after)

async def setup(bot):
    await bot.add_cog(Voice(bot))