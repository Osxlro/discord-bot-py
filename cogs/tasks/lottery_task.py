import random
import logging
from discord.ext import commands, tasks
from services.core import database, lang_service
from services.repositories.user_repository import UserRepository
from services.utils import embed_service

logger = logging.getLogger(__name__)

class LotteryTask(commands.Cog):
    """Tarea en segundo plano para sortear la lotería diaria."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.draw_lottery.start()

    def cog_unload(self):
        self.draw_lottery.cancel()

    @tasks.loop(hours=24)
    async def draw_lottery(self):
        """Bucle diario para seleccionar el ganador de la lotería."""
        await self.bot.wait_until_ready()
        logger.info("🎟️ Iniciando sorteo de lotería diaria...")
        
        try:
            # Obtener todos los participantes
            rows = await database.fetch_all("SELECT user_id, ticket_count FROM raffle_tickets")
            if not rows:
                logger.info("🎟️ No hay participantes en la lotería hoy.")
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
            
            # Calcular pozo acumulado (50 coins por boleto, mínimo 500 coins)
            prize_pool = max(500, total_tickets * 50)
            
            # Entregar premio de forma atómica
            await UserRepository.add_user_coins(winner_id, prize_pool)
            
            # Limpiar boletos para el próximo sorteo
            await database.execute("DELETE FROM raffle_tickets")
            
            # Enviar DM al ganador
            try:
                winner = self.bot.get_user(winner_id)
                if not winner:
                    winner = await self.bot.fetch_user(winner_id)
                    
                if winner:
                    lang = "es" # fallback
                    # Intentar obtener idioma del servidor o del usuario si está registrado
                    user_data = await UserRepository.get_user_data(winner_id)
                    
                    title = "🎟️ ¡Ganaste la Lotería Diaria!"
                    desc = (
                        f"¡Felicidades **{winner.name}**! Has sido seleccionado como el ganador del sorteo diario de **Friday Bot**. 🎉\n\n"
                        f"> 🪙 **Premio recibido:** `{prize_pool}` coins\n"
                        f"> 🎟️ **Tus boletos:** {winner_tickets}\n"
                        f"> 📈 **Total de boletos en juego:** {total_tickets}\n\n"
                        f"El premio ha sido depositado directamente en tu cartera global. ¡Sigue participando!"
                    )
                    
                    embed = embed_service.success(title, desc)
                    await winner.send(embed=embed)
                    logger.info(f"🎟️ Notificación de lotería enviada con éxito a {winner.name} ({winner_id}). Premio: {prize_pool} coins.")
            except Exception as e:
                logger.error(f"❌ Error al enviar notificación DM de lotería al ganador {winner_id}: {e}")
                
        except Exception as e:
            logger.exception(f"❌ Error inesperado en el sorteo de lotería: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(LotteryTask(bot))
