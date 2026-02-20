import gc
import asyncio
import logging
import wavelink
from discord.ext import commands, tasks
from services.core import db_service
from services.features import music_service
from services.utils import voice_service
from config import settings

logger = logging.getLogger(__name__)

class OptimizationTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache_flush_loop.start()    # Guardado rápido (60s)
        self.memory_cleanup_loop.start() # Limpieza profunda (6h)
        self.network_optimization_loop.start() # Limpieza de red (5m)

    def cog_unload(self):
        self.cache_flush_loop.cancel()
        self.memory_cleanup_loop.cancel()
        self.network_optimization_loop.cancel()

    # TAREA 1: Guardado de datos (Frecuente - cada 60s)
    # Evita perder XP si el bot se reinicia.
    @tasks.loop(seconds=settings.OPTIMIZATION_CONFIG["FLUSH_INTERVAL"])
    async def cache_flush_loop(self):
        try:
            await db_service.flush_xp_cache()
        except Exception as e:
            logger.error(f"⚠️ Error guardando XP caché: {e}")

    @cache_flush_loop.error
    async def cache_flush_error(self, error):
        logger.critical(f"🔥 Error CRÍTICO en tarea de guardado (Flush): {error}")
        # La tarea intentará reiniciarse automáticamente en la siguiente iteración si no se cancela

    # TAREA 2: Limpieza de RAM (Lenta - cada 6 horas)
    # Libera memoria acumulada de configuraciones viejas.
    @tasks.loop(hours=settings.OPTIMIZATION_CONFIG["CLEANUP_INTERVAL"])
    async def memory_cleanup_loop(self):
        try:
            # 1. Guardamos todo antes de limpiar por seguridad
            await db_service.flush_xp_cache()
            
            # 2. Mantenimiento de Base de Datos (Ligero)
            # PRAGMA optimize es recomendado por SQLite para apps de larga ejecución
            await db_service.execute("PRAGMA optimize")
            
            # 3. Limpieza de persistencia binaria antigua (Mantenido por 3 días)
            await db_service.prune_old_persistence(days=3)
            
            # 4. Limpiamos el caché de configuración (se recargará bajo demanda)
            if hasattr(db_service, 'clear_memory_cache'):
                db_service.clear_memory_cache()
            
            # 5. Limpiamos usuarios inactivos de la RAM (XP Cache)
            if hasattr(db_service, 'clear_xp_cache_safe'):
                db_service.clear_xp_cache_safe()
            
            # 6. Forzamos a Python a liberar memoria no usada
            await asyncio.to_thread(gc.collect)
            logger.info("🧹 [Optimization] Mantenimiento integral completado (DB optimizada y RAM liberada).")
        except Exception as e:
            logger.error(f"⚠️ Error en limpieza de memoria: {e}")

    @memory_cleanup_loop.error
    async def memory_cleanup_error(self, error):
        logger.critical(f"🔥 Error CRÍTICO en tarea de limpieza (Cleanup): {error}")

    # TAREA 3: Optimización de Red (Cada 5 minutos)
    # Desconecta el bot de canales vacíos para reducir tráfico inbound/outbound innecesario.
    @tasks.loop(minutes=5)
    async def network_optimization_loop(self):
        try:
            for guild in self.bot.guilds:
                player = guild.voice_client
                
                # Si el bot está conectado pero solo (sin humanos)
                if player and player.channel:
                    # Si el guild está en voice_targets, es un modo AFK intencional. No desconectar.
                    if guild.id in voice_service.voice_targets:
                        continue

                    # Filtrar bots para contar solo humanos
                    human_members = [m for m in player.channel.members if not m.bot]
                    if not human_members:
                        if isinstance(player, wavelink.Player):
                            await music_service.cleanup_player(player)
                        await player.disconnect()
                        logger.info(f"🔌 [Network Opt] Desconectado de {guild.name} (Canal vacío).")
        except Exception as e:
            logger.error(f"⚠️ Error en optimización de red: {e}")

    @cache_flush_loop.before_loop
    async def before_flush(self):
        await self.bot.wait_until_ready()
        
    @memory_cleanup_loop.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(OptimizationTasks(bot))