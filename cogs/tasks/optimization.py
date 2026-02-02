import gc
import logging
import discord
from discord.ext import commands, tasks
from services import db_service

logger = logging.getLogger(__name__)

class OptimizationTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache_flush_loop.start()    # Guardado rápido (60s)
        self.memory_cleanup_loop.start() # Limpieza profunda (6h)

    def cog_unload(self):
        self.cache_flush_loop.cancel()
        self.memory_cleanup_loop.cancel()

    # TAREA 1: Guardado de datos (Frecuente - cada 60s)
    # Evita perder XP si el bot se reinicia.
    @tasks.loop(seconds=60)
    async def cache_flush_loop(self):
        try:
            await db_service.flush_xp_cache()
        except Exception as e:
            logger.error(f"⚠️ Error guardando XP caché: {e}")

    # TAREA 2: Limpieza de RAM (Lenta - cada 6 horas)
    # Libera memoria acumulada de configuraciones viejas.
    @tasks.loop(hours=6)
    async def memory_cleanup_loop(self):
        try:
            # 1. Guardamos todo antes de limpiar por seguridad
            await db_service.flush_xp_cache()
            
            # 2. Limpiamos el caché de configuración (se recargará si es necesario)
            if hasattr(db_service, 'clear_memory_cache'):
                db_service.clear_memory_cache()
            
            # 3. Limpiamos usuarios inactivos de la RAM (XP Cache)
            if hasattr(db_service, 'clear_xp_cache_safe'):
                db_service.clear_xp_cache_safe()
            
            # 4. Forzamos a Python a liberar memoria no usada
            gc.collect()
            logger.info("🧹 [Sistema] Mantenimiento de memoria completado (RAM liberada).")
        except Exception as e:
            logger.error(f"⚠️ Error en limpieza de memoria: {e}")

    @cache_flush_loop.before_loop
    async def before_flush(self):
        await self.bot.wait_until_ready()
        
    @memory_cleanup_loop.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(OptimizationTasks(bot))