import discord
import logging
from discord.ext import commands
from discord import app_commands
from services import embed_service, lang_service

class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    async def _get_lang(self, interaction_or_ctx):
        # Helper para sacar el idioma ya sea de interaction o context
        guild = interaction_or_ctx.guild
        return await lang_service.get_guild_lang(guild.id) if guild else "es"

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        lang = await self._get_lang(interaction)
        error_title = lang_service.get_text("error_title", lang)

        if isinstance(error, app_commands.MissingPermissions):
            msg = lang_service.get_text("error_no_perms", lang)
            await interaction.response.send_message(embed=embed_service.error(error_title, msg), ephemeral=True)
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = lang_service.get_text("error_cooldown", lang, seconds=round(error.retry_after, 1))
            await interaction.response.send_message(embed=embed_service.error(error_title, msg), ephemeral=True)
        else:
            logging.error(f"Error: {error}")
            msg = lang_service.get_text("error_generic", lang)
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed_service.error(error_title, msg), ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if hasattr(ctx.command, 'on_error'): return
        lang = await self._get_lang(ctx)
        error_title = lang_service.get_text("error_title", lang)

        if isinstance(error, commands.MissingPermissions):
            msg = lang_service.get_text("error_no_perms", lang)
            await ctx.reply(embed=embed_service.error(error_title, msg), delete_after=10)
        elif isinstance(error, commands.CommandOnCooldown):
            msg = lang_service.get_text("error_cooldown", lang, seconds=round(error.retry_after, 1))
            await ctx.reply(embed=embed_service.error(error_title, msg), delete_after=10)

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))