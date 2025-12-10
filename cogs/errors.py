import discord
import logging
from discord.ext import commands
from discord import app_commands

class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Sobrescribimos el manejador de errores del árbol de comandos (Slash)
        # para que use nuestra función personalizada definida abajo.
        bot.tree.on_error = self.on_app_command_error

    # --- 1. Manejador para Comandos de Barra (Slash Commands) ---
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Maneja errores generados por comandos / (Slash)"""
        
        # Si el comando tiene su propio manejador local, lo ignoramos aquí
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original

        # Error: El usuario no tiene permisos
        if isinstance(error, app_commands.MissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            embed = discord.Embed(
                title="⛔ Permisos Insuficientes",
                description=f"Necesitas los siguientes permisos para usar esto:\n**{', '.join(missing)}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Error: El BOT no tiene permisos para ejecutar la acción
        elif isinstance(error, app_commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            embed = discord.Embed(
                title="⛔ Me faltan permisos",
                description=f"No puedo hacer esto porque me faltan permisos:\n**{', '.join(missing)}**",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        # Error genérico no controlado (Bugs de código)
        else:
            # Registramos el error en la consola/log para el desarrollador
            logging.error(f"Error en comando Slash '{interaction.command.name}': {error}", exc_info=True)
            
            embed = discord.Embed(
                title="💥 Error Inesperado",
                description="Ocurrió un error interno al ejecutar este comando. El administrador ha sido notificado.",
                color=discord.Color.dark_red()
            )
            # Intentamos responder, si ya respondimos usamos follow up
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- 2. Manejador para Comandos de Prefijo (Legacy '!') ---
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Maneja errores generados por comandos de prefijo (!comando)"""

        # Evitamos que el error se propague si ya fue manejado localmente
        if hasattr(ctx.command, 'on_error'):
            return

        # Ignoramos si el error es "Comando no encontrado" (para no spamear el chat)
        if isinstance(error, commands.CommandNotFound):
            return 

        # Extraemos el error original si está empaquetado
        error = getattr(error, 'original', error)

        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("⛔ No tienes permisos para usar este comando.", delete_after=10)

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("⛔ No tengo permisos suficientes en este canal.", delete_after=10)
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"⚠️ Te faltan argumentos. Uso correcto: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", delete_after=10)

        else:
            logging.error(f"Error en comando prefijo '{ctx.command}': {error}", exc_info=True)
            await ctx.reply("💥 Ocurrió un error desconocido. Revisa la consola.", delete_after=10)

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))