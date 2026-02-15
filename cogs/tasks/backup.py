import asyncio
import datetime
import logging
import pathlib
import shutil
import discord
from discord.ext import commands, tasks
from config import settings
from services import db_service, lang_service

logger = logging.getLogger(__name__)

class Backup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backup_db.start()
        self.flush_xp.start()

    def cog_unload(self):
        self.backup_db.cancel()
        self.flush_xp.cancel()

    async def _cleanup_dm(self, channel: discord.DMChannel):
        """Limpia backups antiguos y otros mensajes basura del bot en DMs."""
        backups_encontrados = []
        async for message in channel.history(limit=settings.BACKUP_CONFIG["HISTORY_LIMIT"]):
            if message.author.id != self.bot.user.id:
                continue
            
            # Identificar si es un backup preestablecido (con archivo y palabra clave)
            es_backup = len(message.attachments) > 0 and settings.BACKUP_CONFIG["KEYWORD"] in message.content
            
            if es_backup:
                backups_encontrados.append(message)
            else:
                # Cualquier otro mensaje del bot se considera basura en el canal de backups
                try:
                    await message.delete()
                    await asyncio.sleep(0.5)
                except discord.HTTPException:
                    pass

        if len(backups_encontrados) > settings.BACKUP_CONFIG["MAX_BACKUPS_TO_KEEP"]:
            for msg in backups_encontrados[settings.BACKUP_CONFIG["MAX_BACKUPS_TO_KEEP"]:]:
                try:
                    await msg.delete()
                    await asyncio.sleep(1)
                except discord.HTTPException:
                    pass

    @tasks.loop(minutes=settings.BACKUP_CONFIG["XP_FLUSH_MINUTES"])
    async def flush_xp(self):
        """Guarda el caché de XP en la base de datos periódicamente."""
        await db_service.flush_xp_cache()

    @tasks.loop(hours=settings.BACKUP_CONFIG["INTERVAL_HOURS"])
    async def backup_db(self):
        await self.bot.wait_until_ready()
        
        # Rutas usando pathlib
        db_path = pathlib.Path(settings.BASE_DIR) / settings.DB_CONFIG["DIR_NAME"] / settings.DB_CONFIG["FILE_NAME"]
        temp_backup_path = db_path.with_name(settings.DB_CONFIG["TEMP_BACKUP_NAME"])
        
        if not db_path.exists():
            return

        try:
            # 1. Forzar el guardado de la XP que está en RAM a la DB antes del backup
            await db_service.flush_xp_cache()

            app_info = await self.bot.application_info()
            owner = app_info.owner
            
            # --- LÓGICA DE 24 HORAS ---
            # Buscamos el último backup en el DM
            ultimo_backup = None
            dm_channel = await owner.create_dm()
            
            # Revisamos el historial reciente para no saturar al dueño con archivos duplicados.
            async for message in dm_channel.history(limit=settings.BACKUP_CONFIG["DM_HISTORY_LIMIT"]): 
                if message.author.id == self.bot.user.id and len(message.attachments) > 0 and settings.BACKUP_CONFIG["KEYWORD"] in message.content:
                    ultimo_backup = message
                    break
            
            # Si existe un backup previo, verificamos la fecha
            if ultimo_backup:
                now = datetime.datetime.now(datetime.timezone.utc)
                diff = now - ultimo_backup.created_at
                # Si han pasado menos de 23.5 horas, abortamos (damos margen de 30min)
                if diff.total_seconds() < settings.BACKUP_CONFIG["COOLDOWN_SECONDS"]: 
                    return 

            # 2. Crear copia temporal para evitar bloqueos/corrupción durante el envío
            await asyncio.to_thread(shutil.copy2, db_path, temp_backup_path)

            # 3. ENVIAR BACKUP
            fecha = datetime.date.today().strftime("%Y-%m-%d")
            archivo = discord.File(temp_backup_path, filename=f"backup_{fecha}.sqlite3")
            msg = await owner.send(content=lang_service.get_text("backup_msg", settings.GENERAL_CONFIG["DEFAULT_LANG"], date=fecha), file=archivo)
            
            await self._cleanup_dm(msg.channel)
            logger.info(f"✅ Backup de base de datos enviado a {owner.name}")

        except Exception as e:
            logger.error(f"❌ Error en el sistema de Backup: {e}")
        finally:
            # 4. Limpiar el archivo temporal siempre
            if temp_backup_path.exists():
                temp_backup_path.unlink()

async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))