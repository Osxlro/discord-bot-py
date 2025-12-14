import discord
from discord.ext import commands, tasks
import shutil
import os
import datetime
from config import settings

class Backup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backup_db.start()

    def cog_unload(self):
        self.backup_db.cancel()

    @tasks.loop(hours=24)
    async def backup_db(self):
        await self.bot.wait_until_ready()
        # Directorios
        source = os.path.join(settings.BASE_DIR, "data", "database.sqlite3")
        backup_dir = os.path.join(settings.BASE_DIR, "data", "backups")
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        # Nombre del archivo con fecha: backup_2023-10-25.sqlite3
        fecha = datetime.date.today().strftime("%Y-%m-%d")
        dest = os.path.join(backup_dir, f"backup_{fecha}.sqlite3")
        
        if os.path.exists(source):
            try:
                # Ejecutamos la copia en un hilo aparte para no bloquear el bot
                await self.bot.loop.run_in_executor(None, shutil.copy2, source, dest)
                print(f"📦 [Backup] Base de datos respaldada en: {dest}")
                
                # Limpieza: Borrar backups antiguos (más de 7 días)
                self.limpiar_backups_antiguos(backup_dir)
            except Exception as e:
                print(f"❌ [Backup] Error: {e}")
        
        try:
            # BUSCAR AL DUEÑO DEL BOT
            # Nota: Asegúrate de que tu ID sea obtenible. 
            # Si tienes problemas, pon tu ID fijo: user = await self.bot.fetch_user(123456789)
            app_info = await self.bot.application_info()
            owner = app_info.owner

            fecha = datetime.date.today().strftime("%Y-%m-%d")
            
            # Enviar archivo por DM
            archivo = discord.File(source, filename=f"backup_{fecha}.sqlite3")
            await owner.send(content=f"📦 **Copia de seguridad automática** del día {fecha}.", file=archivo)
            print(f"✅ Backup enviado a {owner.name}")

        except Exception as e:
            print(f"❌ Error al enviar backup: {e}")

    def limpiar_backups_antiguos(self, directorio):
        # Lógica simple para no llenar el disco
        pass # Implementar si se desea borrar archivos viejos

async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))