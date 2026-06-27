import discord
import json
from services.core import lang_service
from services.utils import embed_service
from config import settings

class ConfirmPurchaseView(discord.ui.View):
    """Vista de confirmación de compra de tipo efímera."""
    def __init__(self, bot: discord.Client, item: dict, quantity: int, author_id: int, lang: str):
        super().__init__(timeout=60.0)
        self.bot = bot
        self.item = item
        self.quantity = quantity
        self.author_id = author_id
        self.lang = lang
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(lang_service.get_text("dev_interaction_error", self.lang), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Deshabilitar botones
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        from services.features import shop_service
        success, error, embed = await shop_service.process_purchase(
            interaction.user.id, self.item["item_id"], self.quantity, self.lang
        )

        if not success:
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Notificación efímera de éxito
        await interaction.followup.send(embed=embed, ephemeral=True)

        # Mensaje público en el canal
        from services.features.shop_service import get_localized_field
        item_name = get_localized_field(self.item, "names", self.lang)
        item_emoji = self.item.get("emoji") or ""
        
        public_msg = lang_service.get_text(
            "shop_purchase_public", 
            self.lang, 
            user=interaction.user.mention, 
            qty=self.quantity, 
            emoji=item_emoji, 
            item=item_name
        )
        
        # Enviar de forma general en el canal
        try:
            public_embed = embed_service.success(
                lang_service.get_text("shop_purchase_title", self.lang),
                public_msg
            )
            await interaction.channel.send(content=f"🎉 {interaction.user.mention}", embed=public_embed)
        except Exception:
            pass # Si falla por falta de permisos de envío, ignorar

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        cancel_embed = embed_service.info(
            lang_service.get_text("shop_purchase_title", self.lang),
            lang_service.get_text("shop_purchase_cancelled", self.lang),
            lite=True
        )
        await interaction.followup.send(embed=cancel_embed, ephemeral=True)


class ItemSelect(discord.ui.Select):
    """Menú de selección de objetos para la compra en la página actual de la tienda."""
    def __init__(self, bot: discord.Client, items: list[dict], author_id: int, lang: str):
        self.bot = bot
        self.items_map = {item["item_id"]: item for item in items}
        self.author_id = author_id
        self.lang = lang

        from services.features.shop_service import get_localized_field
        options = []
        for item in items:
            name = get_localized_field(item, "names", lang)
            cost = item["cost"]
            emoji = item.get("emoji") or None
            
            label = f"{name[:50]} ({cost} coins)"
            description = get_localized_field(item, "descs", lang)[:100]
            options.append(discord.SelectOption(
                label=label, 
                value=item["item_id"], 
                description=description, 
                emoji=emoji
            ))

        placeholder = lang_service.get_text("shop_select_placeholder", lang)
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        item = self.items_map[item_id]

        # Crear confirmación de compra efímera
        from services.features.shop_service import get_localized_field
        item_name = get_localized_field(item, "names", self.lang)
        item_emoji = item.get("emoji") or ""
        
        confirm_msg = lang_service.get_text(
            "shop_purchase_confirm", 
            self.lang, 
            qty=1, 
            emoji=item_emoji, 
            item=item_name, 
            cost=item["cost"]
        )
        
        confirm_embed = embed_service.info(
            title=lang_service.get_text("shop_purchase_title", self.lang),
            description=confirm_msg,
            thumbnail=self.bot.user.display_avatar.url
        )

        view = ConfirmPurchaseView(self.bot, item, 1, self.author_id, self.lang)
        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)
        view.message = interaction


class CategoryButton(discord.ui.Button):
    """Botón para seleccionar una categoría en la tienda."""
    def __init__(self, category: str, label: str, active: bool):
        style = discord.ButtonStyle.success if active else discord.ButtonStyle.secondary
        super().__init__(label=label, style=style, row=0)
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.selected_category = self.category
        view.current_page = 0
        view.update_components()
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


class ShopView(discord.ui.View):
    """Vista principal de la tienda con selección de categorías por botones y selector de objetos."""
    def __init__(self, bot: discord.Client, all_items: list[dict], author_id: int, lang: str):
        super().__init__(timeout=settings.GLOBAL_TIMEOUT)
        self.bot = bot
        self.all_items = all_items
        self.author_id = author_id
        self.lang = lang
        
        # Obtener categorías únicas
        self.categories = sorted(list({item.get("category", "Otros") for item in all_items}))
        self.selected_category = self.categories[0] if self.categories else "Otros"
        
        self.current_page = 0
        self.items_per_page = 5
        
        self.btn_prev.label = lang_service.get_text("pagination_prev", lang) or "Anterior"
        self.btn_next.label = lang_service.get_text("pagination_next", lang) or "Siguiente"
        
        self.update_components()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(lang_service.get_text("dev_interaction_error", self.lang), ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass

    def get_filtered_items(self) -> list[dict]:
        return [item for item in self.all_items if item.get("category", "Otros") == self.selected_category]

    def update_components(self):
        # 1. Limpiar componentes dinámicos
        for child in list(self.children):
            if isinstance(child, CategoryButton) or isinstance(child, ItemSelect):
                self.remove_item(child)

        # 2. Agregar botones de categoría
        for cat in self.categories:
            active = (cat == self.selected_category)
            btn = CategoryButton(cat, cat, active)
            self.add_item(btn)

        # 3. Filtrar ítems por la categoría seleccionada
        filtered = self.get_filtered_items()
        self.total_pages = max(1, (len(filtered) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page >= self.total_pages:
            self.current_page = self.total_pages - 1
        if self.current_page < 0:
            self.current_page = 0

        # Habilitar/Deshabilitar botones de paginación
        self.btn_prev.disabled = (self.current_page == 0)
        self.btn_next.disabled = (self.current_page >= self.total_pages - 1)

        # 4. Añadir selector para la página actual
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = filtered[start:end]

        if page_items:
            select = ItemSelect(self.bot, page_items, self.author_id, self.lang)
            self.add_item(select)

    def get_embed(self) -> discord.Embed:
        """Genera el embed de catálogo de la tienda para la página y categoría actuales."""
        title = lang_service.get_text("shop_title", self.lang)
        
        filtered = self.get_filtered_items()
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = filtered[start:end]

        from services.features.shop_service import get_localized_field

        desc = f"### 📂 {self.selected_category}\n"
        for item in page_items:
            emoji = item.get("emoji") or ""
            name = get_localized_field(item, "names", self.lang)
            cost = item["cost"]
            description = get_localized_field(item, "descs", self.lang)
            
            desc += f"> **{emoji} {name}** — `{cost}` coins\n"
            desc += f"> *{description}*\n"
            desc += "\n"

        if not page_items:
            desc = lang_service.get_text("shop_empty", self.lang)

        # Usar helper de info de embed_service
        embed = embed_service.info(
            title=title,
            description=desc,
            thumbnail=self.bot.user.display_avatar.url,
            footer=f"Pág. {self.current_page + 1}/{self.total_pages}"
        )
        return embed

    @discord.ui.button(style=discord.ButtonStyle.primary, row=1)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_components()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary, row=1)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_components()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
