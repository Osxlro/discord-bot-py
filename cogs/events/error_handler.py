import discord
import logging
from difflib import SequenceMatcher
from discord.ext import commands
from discord import app_commands
from services import embed_service, lang_service

logger = logging.getLogger(__name__)

class GlobalErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Vincular el manejador de errores para Slash Commands (AppTree)
        bot.tree.on_error = self.on_app_command_error

    async def _get_lang(self, interaction_or_ctx):
        """Helper para obtener el idioma del servidor o el por defecto."""
        guild = interaction_or_ctx.guild
        return await lang_service.get_guild_lang(guild.id) if guild else "es"

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Manejador global de errores para comandos de prefijo."""
        if hasattr(ctx.command, 'on_error'): return
        
        lang = await self._get_lang(ctx)
        error_title = lang_service.get_text("error_title", lang)

        if isinstance(error, commands.CommandNotFound):
            invoked_with = ctx.invoked_with
            
            # Determinar el espacio de búsqueda: Comandos globales o subcomandos de un grupo
            if ctx.command and isinstance(ctx.command, commands.Group):
                search_space = [cmd.name for cmd in ctx.command.commands if not cmd.hidden]
                parent_prefix = f"{ctx.command.qualified_name} "
            else:
                search_space = [cmd.name for cmd in self.bot.commands if not cmd.hidden]
                parent_prefix = ""
            
            best_match = None
            highest_ratio = 0.0
            
            for cmd_name in search_space:
                ratio = SequenceMatcher(None, invoked_with, cmd_name).ratio()
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    best_match = cmd_name
            
            if best_match and highest_ratio >= 0.6:
                suggestion = f"{parent_prefix}{best_match}"
                msg = lang_service.get_text("error_did_you_mean", lang, suggestion=suggestion)
                # En comandos de prefijo no existe 'ephemeral', usamos delete_after para limpiar el chat
                return await ctx.send(embed=embed_service.info(error_title, msg, lite=True), delete_after=20)
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            usage = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            msg = f"{lang_service.get_text('error_missing_args', lang)}\n\n{lang_service.get_text('error_usage', lang)}\n`{usage}`"
            return await ctx.send(embed=embed_service.error(error_title, msg, lite=True))

        if isinstance(error, commands.BadArgument):
            msg = lang_service.get_text("error_bad_arg", lang)
            return await ctx.send(embed=embed_service.error(error_title, msg, lite=True))

        if isinstance(error, commands.CommandOnCooldown):
            msg = lang_service.get_text("error_cooldown", lang, seconds=round(error.retry_after, 1))
            return await ctx.send(embed=embed_service.error(error_title, msg, lite=True), delete_after=5)

        if isinstance(error, commands.MissingPermissions):
            msg = lang_service.get_text("error_no_perms", lang)
            return await ctx.send(embed=embed_service.error(error_title, msg, lite=True))
            
        if isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            msg = f"{lang_service.get_text('error_bot_no_perms', lang)}\n`{perms}`"
            return await ctx.send(embed=embed_service.error(error_title, msg, lite=True))

        if isinstance(error, commands.NSFWChannelRequired):
            return await ctx.send("🔞 Este comando solo puede usarse en canales NSFW.")

        logger.error(f"🔥 Error en comando de prefijo '{ctx.command}': {error}", exc_info=error)
        await ctx.send(embed=embed_service.error(error_title, lang_service.get_text("error_generic", lang)))

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Manejador global de errores para Slash Commands."""
        lang = await self._get_lang(interaction)
        error_title = lang_service.get_text("error_title", lang)

        # Extraer el error real si está envuelto en CommandInvokeError
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original

        # Ignorar errores de interacción desconocida (común en autocompletado rápido)
        if isinstance(error, discord.NotFound) and error.code == 10062:
            return

        if isinstance(error, app_commands.MissingPermissions):
            msg = lang_service.get_text("error_no_perms", lang)
        elif isinstance(error, app_commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            msg = f"{lang_service.get_text('error_bot_no_perms', lang)}\n`{perms}`"
        elif isinstance(error, app_commands.TransformerError):
            # Error al convertir argumentos en Slash Commands
            msg = lang_service.get_text("error_bad_arg", lang)
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = lang_service.get_text("error_cooldown", lang, seconds=round(error.retry_after, 1))
        else:
            logger.error(f"🔥 Error en Slash Command: {error}", exc_info=error)
            msg = lang_service.get_text("error_generic", lang)

        # Responder de forma segura
        try:
            embed = embed_service.error(error_title, msg)
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except: pass

async def setup(bot):
    await bot.add_cog(GlobalErrorHandler(bot))