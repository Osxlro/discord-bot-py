import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services.features import developer_service
from config import settings
from services.core import lang_service
from services.utils import embed_service, pagination_service

logger = logging.getLogger(__name__)

class Developer(commands.Cog):
    """
    Cog de administración y desarrollo.
    Contiene comandos para gestionar el estado del bot, monitorizar el sistema
    y realizar tareas de mantenimiento técnico.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="status", description="Gestiona los estados rotativos del bot.")
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    async def status_group(self, ctx: commands.Context):
        """Grupo de comandos para la gestión de la presencia (status) del bot."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @status_group.command(name="listar", description="Muestra la lista de estados configurados.")
    async def listar(self, ctx: commands.Context):
        """
        Muestra todos los estados almacenados en la base de datos.
        La respuesta es efímera para no saturar el canal público.
        """
        # Obtener el idioma configurado para el servidor o el por defecto
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Delegar la obtención del embed al servicio
        embed = await developer_service.handle_list_statuses(lang)
        await ctx.send(embed=embed, ephemeral=True)

    @status_group.command(name="agregar", description="Añade un nuevo estado a la rotación.")
    @app_commands.describe(tipo="Actividad", texto="Lo que se mostrará")
    async def agregar(self, ctx: commands.Context, tipo: Literal["playing", "watching", "listening", "competing"], texto: str):
        """
        Añade una nueva frase a la rotación de estados del bot.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio maneja el guardado en DB y retorna el embed de éxito
        embed = await developer_service.handle_add_status(tipo, texto, str(ctx.author), lang)
        await ctx.send(embed=embed, ephemeral=True)

    @status_group.command(name="eliminar", description="Elimina un estado seleccionándolo de la lista.")
    async def eliminar(self, ctx: commands.Context):
        """
        Muestra un menú desplegable (Select) para eliminar estados existentes.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio prepara la vista interactiva con las opciones de la DB
        view, ph = await developer_service.handle_delete_status_prompt(lang)

        if not view:
            # Si no hay estados que borrar, avisamos al usuario
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_status", lang), lang_service.get_text("status_empty", lang)), ephemeral=True)
        
        view.message = await ctx.send(f"{settings.BOTINFO_CONFIG['SELECT_EMOJI']} **{ph}**", view=view, ephemeral=True)

    @commands.hybrid_command(name="listservers", description="Lista los servidores conectados (Solo Owner).", hidden=True)
    @commands.is_owner()
    async def listservers(self, ctx: commands.Context):
        """
        Lista todos los servidores donde el bot está presente.
        Solo accesible por el dueño del bot.
        """
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Obtener lista paginada de servidores desde el servicio
        pages = await developer_service.handle_list_servers(self.bot, lang)

        if not pages:
            return await ctx.send(embed=embed_service.warning(lang_service.get_text("title_info", lang), lang_service.get_text("dev_servers_none", lang)), ephemeral=True)

        if len(pages) == 1:
            await ctx.send(embed=pages[0], ephemeral=True)
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.send(embed=pages[0], view=view, ephemeral=True)

    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        """
        Sincroniza los comandos de aplicación (Slash Commands) con Discord.
        Útil cuando se añaden o modifican comandos nuevos.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        msg_obj = await ctx.send(lang_service.get_text("dev_sync_start", lang))
        
        # Ejecutar sincronización global
        content, error = await developer_service.handle_sync(self.bot, lang)
        await msg_obj.edit(content=content or error)

    @commands.hybrid_command(name="botinfo", description="Panel de control e información del sistema.")
    async def botinfo(self, ctx: commands.Context):
        """
        Muestra un panel interactivo con estadísticas de uso de CPU, RAM,
        versiones de librerías y tiempos de actividad (Uptime).
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio orquesta la recolección de datos de psutil y la creación de la vista
        embed, view = await developer_service.handle_bot_info(ctx, self.bot, lang)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="db_maintenance", description="Ejecuta mantenimiento (VACUUM) en la base de datos.")
    @commands.is_owner()
    async def db_maintenance(self, ctx: commands.Context):
        """
        Ejecuta el comando VACUUM en SQLite para optimizar el tamaño del archivo
        y defragmentar la base de datos.
        """
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await developer_service.handle_db_maintenance(lang)
        await ctx.send(embed=embed)

    @commands.command(name="restart", hidden=True)
    @commands.is_owner()
    async def restart(self, ctx: commands.Context):
        """
        Reinicia el proceso del bot de forma segura, cerrando la base de datos primero.
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.send(lang_service.get_text("dev_restart_msg", lang))
        # El servicio se encarga de la ejecución del sistema para el reinicio
        await developer_service.restart_bot(str(ctx.author))

    @commands.command(name="shutdown", hidden=True)
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """
        Apaga el bot completamente (útil si usas un gestor de procesos como PM2 o Docker).
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.send(lang_service.get_text("dev_shutdown_msg", lang))
        logger.info(f"🛑 Apagado solicitado por {ctx.author}")
        await self.bot.close()

    @commands.command(name="reload", hidden=True)
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, extension: str):
        """
        Recarga una extensión (Cog) específica sin reiniciar el bot.
        Uso: !reload cogs.commands.cumpleaños
        """
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        try:
            # Intentamos recargar la extensión
            await self.bot.reload_extension(extension)
            await ctx.send(lang_service.get_text("dev_reload_success", lang, extension=extension))
            logger.info(f"🔄 Extensión recargada manualmente: {extension}")
        except Exception as e:
            await ctx.send(lang_service.get_text("dev_reload_error", lang, extension=extension, error=str(e)))
            logger.error(f"❌ Error recargando {extension}: {e}")

    @commands.hybrid_group(name="devedit", description="Comandos de edición de estadísticas para desarrolladores (Solo Owner).")
    @commands.is_owner()
    async def devedit_group(self, ctx: commands.Context):
        """Grupo de comandos para manipular estadísticas de usuarios."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @devedit_group.command(name="coins", description="Establece las monedas de un usuario.")
    @app_commands.describe(usuario="El usuario a editar", cantidad="Cantidad de monedas")
    async def devedit_coins(self, ctx: commands.Context, usuario: discord.Member, cantidad: int):
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = await developer_service.handle_edit_coins(usuario.id, cantidad, lang)
        await ctx.send(embed=embed, ephemeral=True)

    @devedit_group.command(name="xp", description="Establece la XP y el nivel de un usuario en el servidor.")
    @app_commands.describe(usuario="El usuario a editar", xp="Cantidad de XP", nivel="Nivel del usuario")
    async def devedit_xp(self, ctx: commands.Context, usuario: discord.Member, xp: int, nivel: int):
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        if xp < 0 or nivel < 1:
            return await ctx.send("La XP debe ser >= 0 y el nivel >= 1.", ephemeral=True)
        embed = await developer_service.handle_edit_xp(ctx.guild.id, usuario.id, xp, nivel, lang)
        await ctx.send(embed=embed, ephemeral=True)

    @devedit_group.command(name="profile", description="Modifica campos del perfil de un usuario.")
    @app_commands.describe(
        usuario="El usuario a editar",
        campo="Campo del perfil a modificar",
        valor="Nuevo valor (para cumpleaños usa DD/MM, para género usa Hombre/Mujer/etc, para descripción usa texto)"
    )
    async def devedit_profile(self, ctx: commands.Context, usuario: discord.Member, campo: Literal["descripcion", "cumpleanos", "genero"], valor: str):
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed, error = await developer_service.handle_edit_profile(usuario.id, campo, valor, lang)
        if error:
            return await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.send(embed=embed, ephemeral=True)

    @devedit_group.command(name="shop_add", description="Añade o edita un objeto en el catálogo de la tienda.")
    @app_commands.describe(
        item_id="ID único del objeto sin espacios (ej: vip_pass)",
        emoji="Emoji icono del objeto (ej: 🎫)",
        cost="Precio en coins del objeto",
        category="Categoría del objeto (ej: Cosméticos, Rangos, Diversión)",
        availability="Disponibilidad del item (permanent o date_range)",
        start_date="Fecha inicio para date_range (YYYY-MM-DD)",
        end_date="Fecha fin para date_range (YYYY-MM-DD)",
        purchase_limit="Límite máximo de compra por usuario (0 o vacío para ilimitado)",
        total_stock="Stock global disponible (0 o vacío para ilimitado)",
        name="Nombre legible por defecto del objeto",
        description="Descripción legible por defecto del objeto"
    )
    async def devedit_shop_add(
        self,
        ctx: commands.Context,
        item_id: str,
        emoji: str,
        cost: int,
        category: str = "Otros",
        availability: Literal["permanent", "date_range"] = "permanent",
        start_date: str = None,
        end_date: str = None,
        purchase_limit: int = None,
        total_stock: int = None,
        name: str = None,
        description: str = None
    ):
        """Añade o actualiza un objeto en la base de datos de la tienda."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.defer(ephemeral=True)

        p_limit = None if (purchase_limit is None or purchase_limit <= 0) else purchase_limit
        t_stock = None if (total_stock is None or total_stock <= 0) else total_stock
        
        name_val = name or item_id.replace("_", " ").title()
        desc_val = description or "Objeto de la tienda."

        # Registrar en la base de datos
        from services.core import db_service
        await db_service.add_or_update_shop_item(
            item_id=item_id,
            emoji=emoji,
            cost=cost,
            availability=availability,
            start_date=start_date,
            end_date=end_date,
            purchase_limit=p_limit,
            total_stock=t_stock,
            name_default=name_val,
            desc_default=desc_val,
            category=category
        )

        embed = embed_service.success(
            lang_service.get_text("shop_purchase_title", lang),
            lang_service.get_text("shop_admin_add_success", lang, item_id=item_id),
            lite=True
        )
        await ctx.send(embed=embed, ephemeral=True)

    @devedit_group.command(name="shop_remove", description="Elimina un objeto del catálogo de la tienda.")
    @app_commands.describe(item_id="El ID del objeto a eliminar")
    async def devedit_shop_remove(self, ctx: commands.Context, item_id: str):
        """Elimina un objeto de la tienda en la base de datos."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.defer(ephemeral=True)

        from services.core import db_service
        deleted = await db_service.delete_shop_item(item_id)
        if not deleted:
            return await ctx.send(
                embed=embed_service.error(
                    lang_service.get_text("error_title", lang),
                    lang_service.get_text("shop_error_item_not_found", lang),
                    lite=True
                ),
                ephemeral=True
            )

        embed = embed_service.success(
            lang_service.get_text("shop_purchase_title", lang),
            lang_service.get_text("shop_admin_remove_success", lang, item_id=item_id),
            lite=True
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_group(name="dev", description="Comandos de utilidad para desarrolladores (Solo Owner).")
    @commands.is_owner()
    async def dev_group(self, ctx: commands.Context):
        """Grupo de comandos para desarrolladores."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @dev_group.command(name="refresh_shop", description="Sincroniza y recarga el catálogo de la tienda desde shop_items.json.")
    async def refresh_shop(self, ctx: commands.Context):
        """Sincroniza el catálogo de la tienda con shop_items.json."""
        await ctx.defer(ephemeral=True)
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        from services.core import db_service
        success = await db_service.sync_shop_catalog()
        
        if success:
            embed = embed_service.success(
                lang_service.get_text("shop_purchase_title", lang),
                "Catálogo de la tienda sincronizado con éxito desde `shop_items.json`.",
                lite=True
            )
        else:
            embed = embed_service.error(
                lang_service.get_text("error_title", lang),
                "Ocurrió un error al sincronizar el catálogo de la tienda. Revisa la consola/logs.",
                lite=True
            )
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Developer(bot))