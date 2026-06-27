import logging
import datetime
import discord
from services.core import db_service, lang_service
from services.utils import embed_service

logger = logging.getLogger(__name__)

async def process_purchase(user_id: int, item_id: str, quantity: int, lang: str) -> tuple[bool, str | None, discord.Embed]:
    """
    Verifica las restricciones de disponibilidad, stock y saldo de monedas,
    y realiza la compra atómica descontando monedas y añadiendo el objeto al inventario.
    """
    if quantity <= 0:
        err_msg = "Cantidad inválida."
        return False, err_msg, embed_service.error(lang_service.get_text("error_title", lang), err_msg, lite=True)

    # 1. Obtener detalles del objeto
    item = await db_service.get_shop_item(item_id)
    if not item:
        err_msg = lang_service.get_text("shop_error_item_not_found", lang)
        return False, err_msg, embed_service.error(lang_service.get_text("error_title", lang), err_msg, lite=True)

    item_name = item.get("name_default") or lang_service.get_text(item.get("name_key"), lang)
    item_emoji = item.get("emoji") or ""

    # 2. Verificar disponibilidad temporal
    availability = item.get("availability") or "permanent"
    if availability == "date_range":
        start_str = item.get("start_date")
        end_str = item.get("end_date")
        if start_str and end_str:
            try:
                now_date = datetime.date.today()
                start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
                if not (start_date <= now_date <= end_date):
                    err_msg = lang_service.get_text("shop_error_unavailable", lang, item=item_name)
                    return False, err_msg, embed_service.error(lang_service.get_text("error_title", lang), err_msg, lite=True)
            except ValueError:
                logger.error(f"Formato de fecha inválido en el objeto de la tienda {item_id}")

    # 3. Verificar límite de compra por usuario
    purchase_limit = item.get("purchase_limit")
    if purchase_limit is not None and purchase_limit > 0:
        current_owned = await db_service.get_user_item_count(user_id, item_id)
        if current_owned + quantity > purchase_limit:
            err_msg = lang_service.get_text("shop_error_user_limit", lang, item=item_name, limit=purchase_limit)
            return False, err_msg, embed_service.error(lang_service.get_text("error_title", lang), err_msg, lite=True)

    # 4. Verificar stock global
    total_stock = item.get("total_stock")
    if total_stock is not None and total_stock >= 0:
        global_sales = await db_service.get_shop_item_global_sales(item_id)
        if global_sales + quantity > total_stock:
            stock_left = max(0, total_stock - global_sales)
            err_msg = lang_service.get_text("shop_error_no_stock", lang, item=item_name, stock=stock_left)
            return False, err_msg, embed_service.error(lang_service.get_text("error_title", lang), err_msg, lite=True)

    # 5. Verificar saldo de monedas
    total_cost = item["cost"] * quantity
    user_coins = await db_service.get_user_coins(user_id)
    if user_coins < total_cost:
        err_msg = lang_service.get_text("shop_error_no_coins", lang, cost=total_cost, coins=user_coins)
        return False, err_msg, embed_service.error(lang_service.get_text("error_title", lang), err_msg, lite=True)

    # 6. Ejecutar transacción
    try:
        # Descontar saldo
        await db_service.add_user_coins(user_id, -total_cost)
        # Añadir al inventario
        await db_service.add_item_to_inventory(user_id, item_id, quantity)
        
        success_msg = lang_service.get_text(
            "shop_purchase_success", 
            lang, 
            qty=quantity, 
            emoji=item_emoji, 
            item=item_name, 
            cost=total_cost
        )
        
        success_embed = embed_service.success(
            lang_service.get_text("shop_purchase_title", lang),
            success_msg
        )
        return True, None, success_embed
    except Exception as e:
        logger.exception(f"Error procesando la compra de {item_id} para {user_id}: {e}")
        err_msg = lang_service.get_text("error_generic", lang)
        return False, err_msg, embed_service.error(lang_service.get_text("error_title", lang), err_msg, lite=True)
