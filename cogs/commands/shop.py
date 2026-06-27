import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services.core import lang_service, db_service
from services.utils import embed_service
from services.features import shop_service
from ui.games import shop_ui

class Shop(commands.Cog):
    """Cog para gestionar el sistema de tienda y compras del bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="shop", description="Abre la tienda interactiva del servidor.")
    async def shop(self, ctx: commands.Context):
        """Muestra la tienda con el catálogo de objetos y menú de compra."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.defer()

        # Obtener todos los objetos de la tienda de la base de datos
        all_items = await db_service.get_all_shop_items()
        
        if not all_items:
            embed = embed_service.info(
                lang_service.get_text("shop_title", lang),
                lang_service.get_text("shop_empty", lang),
                lite=True
            )
            return await ctx.reply(embed=embed)

        # Generar vista interactiva
        view = shop_ui.ShopView(self.bot, all_items, ctx.author.id, lang)
        embed = view.get_embed()
        view.message = await ctx.reply(embed=embed, view=view)

    @commands.hybrid_command(name="buy", description="Compra un objeto de la tienda directamente.")
    @app_commands.describe(
        item_id="El ID único del objeto que quieres comprar (ej: color_role)",
        cantidad="La cantidad de unidades que deseas adquirir (mínimo 1)"
    )
    async def buy(self, ctx: commands.Context, item_id: str, cantidad: int = 1):
        """Inicia el flujo de confirmación efímera para la compra de un objeto."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)

        if cantidad <= 0:
            return await ctx.reply(
                embed=embed_service.error(
                    lang_service.get_text("error_title", lang),
                    "La cantidad debe ser mayor a 0.",
                    lite=True
                ),
                ephemeral=True
            )

        # Obtener información del item
        item = await db_service.get_shop_item(item_id)
        if not item:
            return await ctx.reply(
                embed=embed_service.error(
                    lang_service.get_text("error_title", lang),
                    lang_service.get_text("shop_error_item_not_found", lang),
                    lite=True
                ),
                ephemeral=True
            )

        item_name = item.get("name_default") or lang_service.get_text(item.get("name_key"), lang)
        item_emoji = item.get("emoji") or ""

        # Crear confirmación de compra efímera
        confirm_msg = lang_service.get_text(
            "shop_purchase_confirm", 
            lang, 
            qty=cantidad, 
            emoji=item_emoji, 
            item=item_name, 
            cost=item["cost"] * cantidad
        )
        
        confirm_embed = discord.Embed(
            title=lang_service.get_text("shop_purchase_title", lang),
            description=confirm_msg,
            color=discord.Color.blue()
        )
        confirm_embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # Usar respuesta efímera para que solo el autor vea el embed de confirmación
        view = shop_ui.ConfirmPurchaseView(self.bot, item, cantidad, ctx.author.id, lang)
        
        # Enviar respuesta efímera dependiente del tipo de interacción
        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)
            view.message = ctx.interaction
        else:
            # Para comandos con prefijo tradicional, enviamos respuesta efímera
            # (en discord.py hybrid context, send con ephemeral=True funciona)
            msg = await ctx.send(embed=confirm_embed, view=view, ephemeral=True)
            view.message = msg

    # --- COMANDOS DE ADMINISTRACIÓN (DEVELOPER ONLY) ---
    @commands.hybrid_group(name="shop_admin", description="Administración de la tienda del bot.")
    @commands.is_owner()
    async def shop_admin(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @shop_admin.command(name="add", description="Añade o actualiza un objeto en el catálogo de la tienda.")
    @app_commands.describe(
        item_id="ID único del objeto sin espacios (ej: vip_pass)",
        emoji="Emoji icono del objeto (ej: 🎫)",
        cost="Precio en coins del objeto",
        availability="Disponibilidad del item (permanent o date_range)",
        start_date="Fecha inicio para date_range (YYYY-MM-DD)",
        end_date="Fecha fin para date_range (YYYY-MM-DD)",
        purchase_limit="Límite máximo de compra por usuario (0 o vacío para ilimitado)",
        total_stock="Stock global disponible (0 o vacío para ilimitado)",
        name="Nombre legible por defecto del objeto",
        description="Descripción legible por defecto del objeto"
    )
    async def admin_add(
        self,
        ctx: commands.Context,
        item_id: str,
        emoji: str,
        cost: int,
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

        # Validaciones de entrada
        p_limit = None if (purchase_limit is None or purchase_limit <= 0) else purchase_limit
        t_stock = None if (total_stock is None or total_stock <= 0) else total_stock
        
        name_val = name or item_id.replace("_", " ").title()
        desc_val = description or "Objeto de la tienda."

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
            desc_default=desc_val
        )

        embed = embed_service.success(
            lang_service.get_text("shop_purchase_title", lang),
            lang_service.get_text("shop_admin_add_success", lang, item_id=item_id),
            lite=True
        )
        await ctx.send(embed=embed, ephemeral=True)

    @shop_admin.command(name="remove", description="Elimina un objeto del catálogo de la tienda.")
    @app_commands.describe(item_id="El ID del objeto a eliminar")
    async def admin_remove(self, ctx: commands.Context, item_id: str):
        """Elimina un objeto de la tienda en la base de datos."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        await ctx.defer(ephemeral=True)

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

async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
