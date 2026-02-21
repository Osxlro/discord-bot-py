import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.features import birthday_service
from services.core import lang_service
from services.utils import embed_service

class Cumpleanos(commands.Cog):
    """
    Cog encargado de la gestión de cumpleaños de los usuarios.
    Permite establecer, eliminar, listar y configurar la privacidad de las fechas.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="birthday", description="Comandos relacionados con cumpleaños.")
    async def cumple(self, ctx: commands.Context):
        """Grupo base para los comandos de cumpleaños."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @cumple.command(name="establish", description="Establece tu cumpleaños.")
    async def establecer(self, ctx: commands.Context, dia: app_commands.Range[int, 1, 31], mes: app_commands.Range[int, 1, 12]):
        """Registra o actualiza la fecha de cumpleaños del usuario."""
        # Obtener idioma del servidor
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Delegar lógica al servicio (validación de fecha y guardado en DB)
        embed, error = await birthday_service.handle_establish_birthday(ctx.author.id, dia, mes, lang)
        
        if error:
            # Responder con error si la fecha es inválida (ej: 31 de febrero)
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error), ephemeral=True)
        
        # Responder con éxito usando el embed generado por la UI
        await ctx.reply(embed=embed)

    @cumple.command(name="delete", description= "Elimina tu cumpleaños, o el de alguien más.")
    async def eliminar(self, ctx: commands.Context, usuario: discord.Member = None):
        """Elimina el registro de cumpleaños de la base de datos."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        target = usuario or ctx.author
        
        # Validación de permisos: Solo el dueño de la cuenta o un administrador pueden borrar el registro
        if target.id != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("error_no_perms", lang)), ephemeral=True)

        # Ejecutar eliminación vía servicio
        embed = await birthday_service.handle_delete_birthday(target.id, lang)
        await ctx.reply(embed=embed)

    @cumple.command(name="privacy", description="Decide si festejar tu cumpleaños o no.")
    async def privacidad(self, ctx: commands.Context, estado: Literal["Visible", "Oculto"]):
        """Configura si el bot debe anunciar el cumpleaños del usuario o mantenerlo privado."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Convertir estado a valor booleano/entero para la DB
        val = 1 if estado == "Visible" else 0
        
        # Actualizar en la base de datos vía servicio
        embed = await birthday_service.handle_privacy_update(ctx.author.id, val, lang)
        await ctx.reply(embed=embed)

    @cumple.command(name="list", description="Revisa la lista de próximos cumpleaños.")
    async def lista(self, ctx: commands.Context):
        """Muestra un listado de los cumpleaños más cercanos en el servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Obtener el embed formateado desde el servicio (que orquesta con birthday_ui)
        embed = await birthday_service.handle_get_upcoming_list(ctx.guild, lang)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    """Función de entrada para cargar el Cog en el bot."""
    await bot.add_cog(Cumpleanos(bot))