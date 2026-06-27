import discord
from discord.ext import commands
from discord import app_commands
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

    async def buy_category_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocompleta las categorías disponibles en la tienda."""
        all_items = await db_service.get_all_shop_items()
        categories = sorted(list({item.get("category", "Otros") for item in all_items}))
        choices = [
            app_commands.Choice(name=cat, value=cat)
            for cat in categories
            if current.lower() in cat.lower()
        ]
        return choices[:25]

    async def buy_object_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocompleta los objetos según la categoría filtrada o general."""
        all_items = await db_service.get_all_shop_items()
        
        # Intentar leer la categoría ingresada en la interacción
        selected_category = getattr(interaction.namespace, "category", None)
        if selected_category:
            all_items = [item for item in all_items if item.get("category", "Otros") == selected_category]

        lang = await lang_service.get_guild_lang(interaction.guild_id)
        from services.features.shop_service import get_localized_field
        choices = []
        for item in all_items:
            name = get_localized_field(item, "names", lang)
            emoji = item.get("emoji") or ""
            display_name = f"{emoji} {name}"[:100]
            if current.lower() in name.lower() or current.lower() in item["item_id"].lower():
                choices.append(app_commands.Choice(name=display_name, value=item["item_id"]))
                
        return choices[:25]

    @commands.hybrid_command(name="buy", description="Compra un objeto de la tienda.")
    @app_commands.describe(
        category="Categoría del objeto para filtrar",
        objeto="Nombre o ID del objeto a comprar",
        qty="Cantidad de unidades a adquirir (mínimo 1)"
    )
    @app_commands.autocomplete(category=buy_category_autocomplete, objeto=buy_object_autocomplete)
    async def buy(self, ctx: commands.Context, category: str = None, objeto: str = None, qty: int = 1):
        """Inicia el flujo de confirmación para comprar un objeto de la tienda."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)

        if not objeto:
            return await ctx.reply(
                embed=embed_service.error(
                    lang_service.get_text("error_title", lang),
                    "Debes especificar el objeto a comprar.",
                    lite=True
                ),
                ephemeral=True
            )

        if qty <= 0:
            return await ctx.reply(
                embed=embed_service.error(
                    lang_service.get_text("error_title", lang),
                    "La cantidad debe ser mayor a 0.",
                    lite=True
                ),
                ephemeral=True
            )

        # 1. Buscar por item_id directo primero
        item = await db_service.get_shop_item(objeto)
        
        # 2. Si no se encontró por ID, buscar por nombre exacto o parcial en la DB
        if not item:
            all_items = await db_service.get_all_shop_items()
            best_match = None
            
            # Filtro por categoría opcional antes de buscar por texto
            if category:
                all_items = [it for it in all_items if it.get("category", "Otros") == category]

            from services.features.shop_service import get_localized_field
            for it in all_items:
                name = get_localized_field(it, "names", lang)
                if name.lower() == objeto.lower() or it["item_id"].lower() == objeto.lower():
                    best_match = it
                    break
            
            if not best_match:
                for it in all_items:
                    name = get_localized_field(it, "names", lang)
                    if objeto.lower() in name.lower():
                        best_match = it
                        break
            
            item = best_match

        if not item:
            return await ctx.reply(
                embed=embed_service.error(
                    lang_service.get_text("error_title", lang),
                    lang_service.get_text("shop_error_item_not_found", lang),
                    lite=True
                ),
                ephemeral=True
            )

        from services.features.shop_service import get_localized_field
        item_name = get_localized_field(item, "names", lang)
        item_emoji = item.get("emoji") or ""

        # Crear confirmación de compra efímera
        confirm_msg = lang_service.get_text(
            "shop_purchase_confirm", 
            lang, 
            qty=qty, 
            emoji=item_emoji, 
            item=item_name, 
            cost=item["cost"] * qty
        )
        
        confirm_embed = embed_service.info(
            title=lang_service.get_text("shop_purchase_title", lang),
            description=confirm_msg,
            thumbnail=self.bot.user.display_avatar.url
        )

        # Confirmación de compra efímera
        view = shop_ui.ConfirmPurchaseView(self.bot, item, qty, ctx.author.id, lang)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)
            view.message = ctx.interaction
        else:
            msg = await ctx.send(embed=confirm_embed, view=view, ephemeral=True)
            view.message = msg

async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
