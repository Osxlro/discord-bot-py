import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.features import profile_service, birthday_service
from services.core import lang_service
from services.utils import embed_service
from config import settings

class Usuario(commands.Cog):
    """
    Cog encargado de la gestion y personalizacion del usuario.
    Permite consultar y configurar el perfil, cumpleanos, genero,
    mensajes personalizados y billetera.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="profile", description="Gestion de perfil de usuario.", fallback="check")
    @app_commands.describe(usuario="El usuario del que quieres ver el perfil (vacio para ver el tuyo)")
    async def profile_group(self, ctx: commands.Context, usuario: discord.User = None):
        """Muestra la tarjeta de perfil con estadisticas globales y del servidor."""
        target = usuario or ctx.author
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed, view = await profile_service.handle_profile(ctx.guild, target, lang, ctx.author.id)
        view.message = await ctx.reply(embed=embed, view=view)

    @profile_group.command(name="desc", description="Cambia la biografia de tu tarjeta.")
    @app_commands.describe(texto="Maximo 200 caracteres.")
    async def set_desc(self, ctx: commands.Context, texto: str):
        """Actualiza la biografia que se muestra en la tarjeta de perfil."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed, error = await profile_service.handle_update_description(ctx.author.id, texto, lang)
        
        if error:
            return await ctx.reply(error, ephemeral=True)
        
        await ctx.reply(embed=embed)

    @profile_group.command(name="message", description="Personaliza tus mensajes de nivel o cumpleanos.")
    @app_commands.describe(
        tipo="¿Que mensaje quieres personalizar?",
        texto="Tu mensaje. Usa {user}, {level} (solo nivel). Escribe 'reset' para borrar."
    )
    async def set_personal_msg(self, ctx: commands.Context, tipo: Literal["Nivel", "Cumpleaños"], texto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await profile_service.handle_update_personal_message(ctx.author.id, tipo, texto, lang)
        await ctx.reply(embed=embed)

    @profile_group.command(name="gender", description="Define tu genero en tu perfil.")
    @app_commands.describe(opcion="Elige tu genero (o 'none' para ocultar)")
    async def set_gender(self, ctx: commands.Context, opcion: Literal["Hombre", "Mujer", "No Binario", "Extraterrestre", "none"]):
        """Actualiza el genero que se muestra en tu tarjeta de perfil."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        mapping = {
            "Hombre": "hombre",
            "Mujer": "mujer",
            "No Binario": "no_binario",
            "Extraterrestre": "extraterrestre",
            "none": "none"
        }
        val = mapping[opcion]
        embed = await profile_service.handle_update_gender(ctx.author.id, val, lang)
        await ctx.reply(embed=embed)

    # --- GRUPO RAÍZ DE CUMPLEAÑOS ---
    @commands.hybrid_group(name="birthday", description="Comandos relacionados con cumpleanos.")
    async def birthday(self, ctx: commands.Context):
        """Grupo base para los comandos de cumpleanos."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @birthday.command(name="establish", description="Establece tu cumpleanos.")
    @app_commands.describe(dia="Dia (1-31)", mes="Mes (1-12)")
    async def establecer(self, ctx: commands.Context, dia: app_commands.Range[int, 1, 31], mes: app_commands.Range[int, 1, 12]):
        """Registra o actualiza la fecha de cumpleanos del usuario."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed, error = await birthday_service.handle_establish_birthday(ctx.author.id, dia, mes, lang)
        
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error), ephemeral=True)
        
        await ctx.reply(embed=embed)

    @birthday.command(name="delete", description="Elimina tu cumpleanos, o el de alguien mas.")
    @app_commands.describe(usuario="Usuario del que deseas eliminar el cumpleanos (solo administradores)")
    async def eliminar(self, ctx: commands.Context, usuario: discord.Member = None):
        """Elimina el registro de cumpleanos de la base de datos."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        target = usuario or ctx.author
        
        if target.id != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("error_no_perms", lang)), ephemeral=True)

        embed = await birthday_service.handle_delete_birthday(target.id, lang)
        await ctx.reply(embed=embed)

    @birthday.command(name="privacy", description="Decide si festejar tu cumpleanos o no.")
    @app_commands.describe(estado="Visibilidad de tu cumpleanos")
    async def privacidad(self, ctx: commands.Context, estado: Literal["Visible", "Oculto"]):
        """Configura si el bot debe anunciar el cumpleanos del usuario o mantenerlo privado."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        val = 1 if estado == "Visible" else 0
        embed = await birthday_service.handle_privacy_update(ctx.author.id, val, lang)
        await ctx.reply(embed=embed)

    @birthday.command(name="list", description="Revisa la lista de proximos cumpleanos.")
    async def lista(self, ctx: commands.Context):
        """Muestra un listado de los cumpleanos mas cercanos en el servidor."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await birthday_service.handle_get_upcoming_list(ctx.guild, lang)
        await ctx.reply(embed=embed)

    # --- COMANDO wallet (BILLETERA INDEPENDIENTE) ---
    @commands.hybrid_command(name="wallet", description="Muestra tus coins y tu cuenta bancaria.")
    @app_commands.describe(usuario="El usuario del que quieres ver la billetera (vacio para ver la tuya)")
    async def wallet(self, ctx: commands.Context, usuario: discord.User = None):
        """Muestra tus coins y el estado de tu cuenta bancaria de forma directa."""
        await ctx.defer()
        target = usuario or ctx.author
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        from services.repositories.user_repository import UserRepository
        user_data = await UserRepository.get_user_data(target.id)
        
        from ui.social import profile_ui
        embed = profile_ui.get_wallet_embed(target, user_data, lang)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Funcion de entrada para cargar el Cog en el bot."""
    await bot.add_cog(Usuario(bot))
