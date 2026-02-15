import logging
from discord.ext import commands
from services.utils import embed_service
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
        
        if not ctx.author.voice:
            msg = lang_service.get_text("voice_error_user", lang)
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg))

        channel = ctx.author.voice.channel
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.connect:
            msg = lang_service.get_text("voice_error_perms", lang)
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg))

        if await voice_service.join_voice(ctx.guild, channel):
            msg = lang_service.get_text("voice_join", lang, channel=channel.name)
            await ctx.send(embed=embed_service.success(lang_service.get_text("voice_title", lang), msg, lite=True))
            logger.info(f"Voice Join: {ctx.guild.name} -> {channel.name}")
        else:
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), "Error al conectar."))

    @commands.hybrid_command(name="leave", description="Desconecta al bot del canal de voz.")
    async def leave(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if await voice_service.leave_voice(ctx.guild):
            msg = lang_service.get_text("voice_leave", lang)
            await ctx.send(embed=embed_service.success(lang_service.get_text("voice_title", lang), msg, lite=True))
            logger.info(f"Voice Leave: {ctx.guild.name}")
        else:
            try: await ctx.message.add_reaction("❓")
            except: pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Detecta desconexiones forzadas o inesperadas."""
        if member.id == self.bot.user.id:
            if before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
                if member.guild.id in voice_service.voice_targets:
                    voice_service.voice_targets[member.guild.id] = after.channel.id
                    logger.info(f"🔄 [Voice] Bot movido manualmente a {after.channel.name} en {member.guild.name}. Objetivo actualizado.")

            elif before.channel is not None and after.channel is None:
                target_channel_id = voice_service.voice_targets.get(member.guild.id)
                if target_channel_id and target_channel_id == before.channel.id:
                    logger.warning(f"⚠️ [Voice] Desconexión inesperada en {member.guild.name}. Iniciando reconexión...")
                    self.bot.loop.create_task(voice_service.reconnect_voice(self.bot, member.guild, target_channel_id))

async def setup(bot):
    await bot.add_cog(Voice(bot))