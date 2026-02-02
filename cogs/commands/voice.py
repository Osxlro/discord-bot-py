import logging
from discord.ext import commands
from services import embed_service, lang_service

logger = logging.getLogger(__name__)

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="join", description="Conecta el bot a tu canal de voz (Modo Chill).")
    async def join(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # 1. Verificar si el usuario tiene canal
        if not ctx.author.voice:
            msg = lang_service.get_text("voice_error_user", lang)
            return await ctx.send(embed=embed_service.error("Error", msg))

        channel = ctx.author.voice.channel

        # 2. Verificar permisos del bot
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.connect:
            msg = lang_service.get_text("voice_error_perms", lang)
            return await ctx.send(embed=embed_service.error("Error", msg))

        # 3. Conectar (u mover si ya está en otro)
        try:
            if ctx.voice_client:
                # Si el cliente está en un estado inconsistente, forzamos desconexión primero
                if not ctx.voice_client.is_connected():
                    await ctx.voice_client.disconnect(force=True)
                    await channel.connect(self_deaf=True, self_mute=True)
                else:
                    await ctx.voice_client.move_to(channel)
                    # Aseguramos que siga en modo "Chill" (Sordo/Mute) al moverse
                    await ctx.guild.me.edit(deafen=True, mute=True)
            else:
                await channel.connect(self_deaf=True, self_mute=True)
            
            msg = lang_service.get_text("voice_join", lang, channel=channel.name)
            await ctx.send(embed=embed_service.success("Voice", msg, lite=True))
            logger.info(f"Voice Join: {ctx.guild.name} -> {channel.name}")
            
        except Exception as e:
            logger.error(f"Error Voice Join en {ctx.guild.name}: {e}")
            await ctx.send(embed=embed_service.error("Error", f"{e}"))

    @commands.hybrid_command(name="leave", description="Desconecta al bot del canal de voz.")
    async def leave(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            msg = lang_service.get_text("voice_leave", lang)
            await ctx.send(embed=embed_service.success("Voice", msg, lite=True))
            logger.info(f"Voice Leave: {ctx.guild.name}")
        else:
            # Si no está conectado, reacciona con un emoji simple
            try: await ctx.message.add_reaction("❓")
            except: pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Detecta desconexiones forzadas o inesperadas."""
        # Si el bot es el que cambió de estado
        if member.id == self.bot.user.id:
            # Si estaba en un canal y ahora no (Desconexión)
            if before.channel is not None and after.channel is None:
                # Aquí podrías implementar lógica de reconexión automática si lo deseas
                logger.warning(f"⚠️ [Voice] Bot desconectado de {before.channel.name} en {member.guild.name}.")

async def setup(bot):
    await bot.add_cog(Voice(bot))