import random
import logging
import discord
from services.core import database, lang_service
from services.repositories.user_repository import UserRepository
from services.utils import embed_service
from config import settings

logger = logging.getLogger(__name__)

async def draw_daily_lottery(bot: discord.Client) -> None:
    """
    Sortea la lotería diaria, entrega el premio al ganador,
    notifica vía DM en su idioma correspondiente y limpia la tabla.
    """
    logger.info("🎟️ [LotteryService] Iniciando sorteo de lotería...")
    
    try:
        # Obtener todos los participantes
        rows = await database.fetch_all("SELECT user_id, ticket_count FROM raffle_tickets")
        if not rows:
            logger.info("🎟️ [LotteryService] No hay participantes en la lotería hoy.")
            return
            
        tickets_pool = []
        total_tickets = 0
        user_tickets_map = {}
        
        for row in rows:
            u_id = row["user_id"]
            count = row["ticket_count"]
            total_tickets += count
            user_tickets_map[u_id] = count
            tickets_pool.extend([u_id] * count)
            
        if not tickets_pool:
            return
            
        # Seleccionar ganador de forma aleatoria
        winner_id = random.choice(tickets_pool)
        winner_tickets = user_tickets_map[winner_id]
        
        # Leer configuración desde settings
        lottery_conf = settings.LOTTERY_CONFIG
        ticket_cost = lottery_conf.get("TICKET_COST", 50)
        min_prize = lottery_conf.get("MIN_PRIZE_POOL", 500)
        
        # Calcular premio
        prize_pool = max(min_prize, total_tickets * ticket_cost)
        
        # Entregar premio de forma atómica
        await UserRepository.add_user_coins(winner_id, prize_pool)
        
        # Limpiar boletos para el próximo sorteo
        await database.execute("DELETE FROM raffle_tickets")
        
        # Enviar DM al ganador
        try:
            winner = bot.get_user(winner_id)
            if not winner:
                winner = await bot.fetch_user(winner_id)
                
            if winner:
                # Intentar obtener idioma del servidor o de las preferencias del usuario
                lang = "es" # fallback
                user_data = await UserRepository.get_user_data(winner_id)
                if user_data:
                    # Encontrar el primer server donde esté el usuario para extraer su idioma o fallback a es
                    pass
                
                # Obtener textos localizados del DM
                title = lang_service.get_text("lottery_win_title", lang)
                desc = lang_service.get_text(
                    "lottery_win_desc",
                    lang,
                    winner=winner.name,
                    prize=prize_pool,
                    tickets=winner_tickets,
                    total=total_tickets
                )
                
                embed = embed_service.success(title, desc)
                await winner.send(embed=embed)
                logger.info(f"🎟️ [LotteryService] Notificación enviada con éxito a {winner.name} ({winner_id}).")
        except Exception as e:
            logger.error(f"❌ [LotteryService] Error al enviar notificación DM al ganador {winner_id}: {e}")
            
    except Exception as e:
        logger.exception(f"❌ [LotteryService] Error inesperado durante el sorteo: {e}")
