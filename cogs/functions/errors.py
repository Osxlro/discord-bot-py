import discord
import logging
from discord.ext import commands
from discord import app_commands
from services import embed_service

class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original

        if isinstance(error, app_commands.MissingPermissions):
            missing = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            embed = embed_service.error(
                "Acceso Denegado",
                f"Lo siento {interaction.user.mention}, no tienes permisos para usar esto.\n\n🔒 **Necesitas:** `{', '.join(missing)}`"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif isinstance(error, app_commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            embed = embed_service.error(
                "Faltan Permisos",
                f"No puedo ejecutar esta orden porque me faltan permisos en este canal.\n\n🤖 **Necesito:** `{', '.join(missing)}`"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif isinstance(error, app_commands.CommandOnCooldown):
            embed = embed_service.error(
                "Estás muy rápido",
                f"Espera un poco antes de volver a usar este comando.\n⏱️ **Tiempo restante:** {error.retry_after:.2f} segundos."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            logging.error(f"Error Slash '{interaction.command.name}': {error}", exc_info=True)
            embed = embed_service.error(
                "Error Inesperado",
                "Ocurrió un problema interno. El desarrollador ha sido notificado."
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if hasattr(ctx.command, 'on_error'):
            return

        if isinstance(error, commands.CommandNotFound):
            return 

        error = getattr(error, 'original', error)

        if isinstance(error, commands.MissingPermissions):
            embed = embed_service.error("Acceso Denegado", "No tienes permisos suficientes para usar este comando.")
            await ctx.reply(embed=embed, delete_after=10)

        elif isinstance(error, commands.BotMissingPermissions):
            embed = embed_service.error("Me faltan permisos", "Verifica mis roles y permisos en este canal.")
            await ctx.reply(embed=embed, delete_after=10)
        
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = embed_service.info(
                "Faltan datos",
                f"Uso correcto:\n`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )
            await ctx.reply(embed=embed, delete_after=15)

        elif isinstance(error, commands.NotOwner):
            embed = embed_service.error("Solo Desarrollador", "Este comando es exclusivo para el dueño del bot.")
            await ctx.reply(embed=embed, delete_after=5)

        else:
            logging.error(f"Error Prefix '{ctx.command}': {error}", exc_info=True)
            embed = embed_service.error("Error", "Ocurrió un error desconocido.")
            await ctx.reply(embed=embed, delete_after=10)

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))