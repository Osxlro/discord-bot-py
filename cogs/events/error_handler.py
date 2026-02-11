import discord
import logging
from discord.ext import commands
from services import embed_service, lang_service

logger = logging.getLogger(__name__)

class GlobalErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Manejador global de errores para comandos de prefijo."""
        if hasattr(ctx.command, 'on_error'): return
        await self._handle_error(ctx, error)

    async def _handle_error(self, ctx, error):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        if isinstance(error, commands.CommandOnCooldown):
            msg = lang_service.get_text("error_cooldown", lang, seconds=round(error.retry_after, 1))
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg, lite=True), delete_after=5)

        if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
            msg = lang_service.get_text("error_no_perms", lang)
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), msg, lite=True))

        if isinstance(error, commands.NSFWChannelRequired):
            return await ctx.send("🔞 Este comando solo puede usarse en canales NSFW.")

        # Errores no controlados
        logger.error(f"🔥 Error no manejado en /{ctx.command}: {error}", exc_info=error)
        try:
            await ctx.send(embed=embed_service.error(
                lang_service.get_text("title_error", lang), 
                lang_service.get_text("error_generic", lang)
            ))
        except: pass

async def setup(bot):
    # Vincular también el error handler de la AppTree (Slash Commands)
    handler = GlobalErrorHandler(bot)
    bot.tree.on_error = handler._handle_error
    await bot.add_cog(handler)