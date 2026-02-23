import logging
import asyncio
import discord
import wavelink
import os
from discord.ext import commands, tasks
from services.features import help_service
from config import settings
from services.core import db_service, lang_service, persistence_service
from services.features import developer_service, level_service, moderation_service, profile_service, diversion_service, setup_service, birthday_service
from services.utils import algorithm_service, voice_service

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
        # Esperar 10 segundos adicionales para permitir que Lavalink y Spotify conecten
        await asyncio.sleep(10)
        logger.debug("🔍 [HealthCheck] Iniciando suite de autodiagnóstico...")
        
        errors = []
        warnings = []

        await self._check_database(errors)
        await self._check_filesystem(errors, warnings)
        await self._check_lavalink(errors)
        await self._check_spotify(errors)
        await self._check_localization_parity(errors)
        await self._check_command_logic(errors, warnings)
        await self._check_system_resources(errors, warnings)

        # --- REPORTE DE RESULTADOS ---
        for w in warnings:
            logger.warning(f"⚠️ [HealthCheck] Advertencia: {w}")

        if not errors:
            logger.debug("✅ [HealthCheck] Suite completada. El sistema se encuentra estable.")
        else:
            for error in errors:
                logger.error(f"❌ [HealthCheck] Bug/Fallo detectado: {error}")
            await self._notify_owner(errors)

    async def _check_database(self, errors):
        # 1. Comprobación de Base de Datos
        try:
            await db_service.fetch_one("SELECT 1")
            # Prueba de integridad física de SQLite
            res = await db_service.fetch_one("PRAGMA integrity_check")
            if res and res[0] != "ok":
                errors.append(f"Database Integrity: {res[0]}")
            
            # Verificar existencia de tablas críticas
            tables = ["users", "guild_stats", "guild_config", "bot_statuses"]
            for table in tables:
                exists = await db_service.fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not exists:
                    errors.append(f"Database Schema: Table '{table}' is missing.")
        except Exception as e:
            errors.append(f"Database Connectivity: {e}")

    async def _check_filesystem(self, errors, warnings):
        # 2. Salud del Sistema de Archivos
        try:
            if os.path.exists(db_service.DB_PATH):
                db_size = os.path.getsize(db_service.DB_PATH) / (1024 * 1024)
                if db_size > 100: warnings.append(f"DB Size: {db_size:.2f}MB")
            
            if os.path.exists(settings.LOG_FILE):
                log_size = os.path.getsize(settings.LOG_FILE) / (1024 * 1024)
                if log_size > 20: warnings.append(f"Log Size: {log_size:.2f}MB")
        except Exception as e:
            errors.append(f"File System Check: {e}")

    async def _check_lavalink(self, errors):
        # 2. Comprobación de Nodos de Música (Lavalink)
        if not wavelink.Pool.nodes:
            errors.append("Music: No hay nodos configurados en el Pool.")
        else:
            active_nodes = [n for n in wavelink.Pool.nodes.values() if n.status == wavelink.NodeStatus.CONNECTED]
            if not active_nodes:
                errors.append("Music: Todos los nodos de Lavalink están desconectados.")

    async def _check_spotify(self, errors):
        # 3. APIs Externas (Spotify)
        if settings.LAVALINK_CONFIG["SPOTIFY"]["CLIENT_ID"]:
            try:
                engine = algorithm_service.RecommendationEngine()
                token = await engine._get_spotify_token()
                if not token:
                    errors.append("Spotify API: No se pudo obtener token de acceso.")
            except Exception as e:
                errors.append(f"Spotify API Error: {e}")

    async def _check_localization_parity(self, errors):
        # 4. Verificación de Paridad de Idiomas
        try:
            from config.lang.es import ES
            from config.lang.en import EN
            from config.lang.pt import PT
            # Intentar importar FR si existe, si no, ignorar
            try: from config.lang.fr import FR
            except ImportError: FR = {}

            langs = {"en": EN, "pt": PT, "fr": FR}
            base_keys = set(ES.keys())

            for code, content in langs.items():
                if not content: continue
                missing = base_keys - set(content.keys())
                if missing:
                    # Reportar solo las primeras 3 para no saturar
                    sample = ", ".join(list(missing)[:3])
                    errors.append(f"Localization: '{code}' le faltan {len(missing)} claves (ej: {sample})")
                
                # Verificar que no haya valores vacíos
                empty = [k for k, v in content.items() if not v and k in base_keys]
                if empty:
                    errors.append(f"Localization: '{code}' tiene claves vacías: {empty[0]}")
        except Exception as e:
            errors.append(f"Localization Parity Check: {e}")

    async def _check_command_logic(self, errors, warnings):
        # 3. Simulación de Comandos Críticos (Dry Run)
        # Intentamos ejecutar la lógica de los servicios que alimentan a los comandos
        test_guild = self.bot.guilds[0] if self.bot.guilds else None
        if test_guild:
            lang = "es" # Idioma base para pruebas
            
            def check_embed(embed, name):
                if not embed or not isinstance(embed, discord.Embed):
                    errors.append(f"Command Logic ({name}): No devolvió un Embed válido.")
                    return False
                # Detectar si hay placeholders sin reemplazar como {user}
                str_embed = str(embed.to_dict())
                if "{" in str_embed and "}" in str_embed:
                    # Filtramos falsos positivos de URLs o sintaxis de dict
                    import re
                    placeholders = re.findall(r'\{([a-zA-Z0-9_]+)\}', str_embed)
                    if placeholders:
                        warnings.append(f"Command Logic ({name}): Posible clave sin reemplazar: {{{placeholders[0]}}}")
                return True

            # Prueba lógica de /help
            try:
                class MockCtx:
                    def __init__(self, g, a):
                        self.guild, self.author = g, a
                embed, _ = await help_service.handle_help(self.bot, MockCtx(test_guild, test_guild.me), lang)
                check_embed(embed, "/help")
            except Exception as e:
                errors.append(f"Command Logic (/help): {e}")

            # Prueba lógica de /perfil
            try:
                embed, _ = await profile_service.handle_profile(test_guild, test_guild.me, lang, self.bot.user.id)
                check_embed(embed, "/perfil")
            except Exception as e:
                errors.append(f"Command Logic (/perfil): {e}")

            # Prueba lógica de Moderación
            try:
                # Aseguramos que parse_time devuelva lo esperado (int o timedelta según tu implementación)
                if int(moderation_service.parse_time("1h")) != 3600:
                    errors.append("Service Logic (Moderation): parse_time falló.")
                embed = moderation_service.get_mod_embed(test_guild, "TestUser", "kick", "TestReason", lang, {})
                check_embed(embed, "Moderation UI")
            except Exception as e:
                errors.append(f"Command Logic (Moderation): {e}")

            # Prueba lógica de Niveles
            try:
                await level_service.get_level_up_message(test_guild.me, 5, lang)
                dummy_rows = [{'user_id': self.bot.user.id, 'xp': 100, 'level': 2, 'rebirths': 0}]
                pages = level_service.get_leaderboard_pages(test_guild, dummy_rows, lang)
                if pages: check_embed(pages[0], "Levels Leaderboard")
            except Exception as e:
                errors.append(f"Command Logic (Levels): {e}")

            # Prueba lógica de Diversión
            try:
                embed = diversion_service.handle_coinflip(lang)
                check_embed(embed, "/coinflip")
            except Exception as e:
                errors.append(f"Command Logic (Diversion): {e}")

            # Prueba lógica de Configuración
            try:
                embed = await setup_service.handle_get_info(test_guild, lang)
                check_embed(embed, "/setup info")
            except Exception as e:
                errors.append(f"Command Logic (Setup): {e}")

            # Prueba lógica de Algoritmo de Música
            try:
                engine = algorithm_service.RecommendationEngine()
                class MockTrack:
                    def __init__(self, t, a, l, i): self.title, self.author, self.length, self.identifier = t, a, l, i
                seed, cand = MockTrack("A", "A", 100, "1"), MockTrack("B", "B", 100, "2")
                engine._calculate_score(cand, seed, set(), "day", {})
            except Exception as e:
                errors.append(f"Command Logic (Algorithm): {e}")

            # Prueba de Persistencia Binaria
            try:
                await persistence_service.store("health_test", "ping", {"status": "ok"})
                if (await persistence_service.load("health_test", "ping"))["status"] != "ok":
                    errors.append("Persistence Service: Data mismatch.")
            except Exception as e:
                errors.append(f"Persistence Service Error: {e}")

            # Verificación de permisos en el servidor de prueba
            perms = test_guild.me.guild_permissions
            if not perms.embed_links or not perms.send_messages:
                warnings.append(f"Permissions: Faltan permisos básicos en {test_guild.name}")

    async def _check_system_resources(self, errors, warnings):
        # 4. Verificación de Latencia
        if self.bot.latency > 1.0: # Más de 1000ms es crítico
            warnings.append(f"Latency: {round(self.bot.latency * 1000)}ms")

        # Verificación de consistencia de Voz
        try:
            for guild_id in list(voice_service.voice_targets.keys()):
                guild = self.bot.get_guild(guild_id)
                if not guild or not guild.voice_client:
                    warnings.append(f"Voice Consistency: Target set for {guild_id} but no voice client found.")
        except Exception as e:
            errors.append(f"Voice Consistency Check: {e}")

        # Verificación de Caché de XP
        try:
            cache_size = len(db_service._xp_cache)
            if cache_size > 500:
                warnings.append(f"XP Cache: {cache_size} entries pending flush.")
        except: pass

        # 5. Recursos del Sistema (vía Developer Service)
        try:
            info = await developer_service.get_psutil_info()
            if info.get("available") and info["ram_sys"].percent > 90:
                warnings.append(f"System RAM: {info['ram_sys'].percent}%")
        except: pass

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