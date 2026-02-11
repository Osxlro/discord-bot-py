import logging
import asyncio
import discord
import wavelink
from discord.ext import commands, tasks
from services import db_service, lang_service, help_service, profile_service
from config import settings

logger = logging.getLogger(__name__)

class HealthCheck(commands.Cog):
    """
    Tarea de diagnóstico automático. 
    Simula el uso de comandos y verifica la salud de los servicios en segundo plano.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.integrity_check.start()

    def cog_unload(self):
        self.integrity_check.cancel()

    @tasks.loop(minutes=30)
    async def integrity_check(self):
        """Ejecuta una suite de pruebas de autodiagnóstico."""
        await self.bot.wait_until_ready()
        logger.info("🔍 [HealthCheck] Iniciando suite de autodiagnóstico...")
        
        errors = []

        # 1. Comprobación de Base de Datos
        try:
            await db_service.fetch_one("SELECT 1")
        except Exception as e:
            errors.append(f"Database: {e}")

        # 2. Comprobación de Nodos de Música (Lavalink)
        if not wavelink.Pool.nodes:
            errors.append("Music: No hay nodos configurados en el Pool.")
        else:
            active_nodes = [n for n in wavelink.Pool.nodes.values() if n.status == wavelink.NodeStatus.CONNECTED]
            if not active_nodes:
                errors.append("Music: Todos los nodos de Lavalink están desconectados.")

        # 3. Simulación de Comandos Críticos (Dry Run)
        # Intentamos ejecutar la lógica de los servicios que alimentan a los comandos
        test_guild = self.bot.guilds[0] if self.bot.guilds else None
        if test_guild:
            lang = "es" # Idioma base para pruebas
            
            # Prueba lógica de /help
            try:
                await help_service.get_home_embed(self.bot, test_guild, test_guild.me, lang)
            except Exception as e:
                errors.append(f"Command Logic (/help): {e}")

            # Prueba lógica de /perfil
            try:
                await profile_service.get_profile_embed(self.bot, test_guild, test_guild.me, lang)
            except Exception as e:
                errors.append(f"Command Logic (/perfil): {e}")

        # 4. Verificación de Latencia
        if self.bot.latency > 1.0: # Más de 1000ms es crítico
            logger.warning(f"⚠️ [HealthCheck] Latencia de Gateway inusualmente alta: {round(self.bot.latency * 1000)}ms")

        # --- REPORTE DE RESULTADOS ---
        if not errors:
            logger.info("✅ [HealthCheck] El sistema se encuentra estable. Todas las pruebas pasaron.")
        else:
            for error in errors:
                logger.error(f"❌ [HealthCheck] Bug/Fallo detectado: {error}")
            
            # Opcional: Notificar al dueño por DM si hay errores críticos
            await self._notify_owner(errors)

    async def _notify_owner(self, errors: list):
        """Envía un reporte de errores al dueño del bot."""
        try:
            app_info = await self.bot.application_info()
            owner = app_info.owner
            
            error_list = "\n".join([f"• {err}" for err in errors])
            embed = discord.Embed(
                title="🚨 Reporte de Errores Automático",
                description=f"Se han detectado anomalías durante el autodiagnóstico:\n\n{error_list}",
                color=discord.Color.red()
            )
            await owner.send(embed=embed)
        except Exception:
            logger.exception("No se pudo notificar al dueño sobre los errores")

async def setup(bot):
    await bot.add_cog(HealthCheck(bot))