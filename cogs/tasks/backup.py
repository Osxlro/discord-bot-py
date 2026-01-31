import discord
from discord.ext import commands, tasks
import os
import datetime
import asyncio
from config import settings

class Backup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backup_db.start()

    def cog_unload(self):
        self.backup_db.cancel()

    async def _cleanup_dm(self, channel: discord.DMChannel):
        """Limpia backups antiguos, manteniendo los 3 más recientes."""
        backups_encontrados = []
        async for message in channel.history(limit=50):
            es_mio = message.author.id == self.bot.user.id
            tiene_archivo = len(message.attachments) > 0
            if es_mio and tiene_archivo and "Backup" in message.content:
                backups_encontrados.append(message)

        if len(backups_encontrados) > 3:
            for msg in backups_encontrados[3:]:
                try:
                    await msg.delete()
                    await asyncio.sleep(1)
                except: pass

    @tasks.loop(hours=12)
    async def backup_db(self):
        await self.bot.wait_until_ready()
        db_path = os.path.join(settings.BASE_DIR, "data", "database.sqlite3")
        
        if not os.path.exists(db_path): return

        try:
            app_info = await self.bot.application_info()
            owner = app_info.owner
            
            # --- LÓGICA DE 24 HORAS ---
            # Buscamos el último backup en el DM
            ultimo_backup = None
            dm_channel = await owner.create_dm()
            
            async for message in dm_channel.history(limit=20):
                if message.author.id == self.bot.user.id and len(message.attachments) > 0 and "Backup" in message.content:
                    ultimo_backup = message
                    break
            
            # Si existe un backup previo, verificamos la fecha
            if ultimo_backup:
                now = datetime.datetime.now(datetime.timezone.utc)
                diff = now - ultimo_backup.created_at
                # Si han pasado menos de 23.5 horas, abortamos (damos margen de 30min)
                if diff.total_seconds() < 84600: 
                    return 

            # --- ENVIAR BACKUP ---
            fecha = datetime.date.today().strftime("%Y-%m-%d")
            archivo = discord.File(db_path, filename=f"backup_{fecha}.sqlite3")
            msg = await owner.send(content=f"📦 **Backup** {fecha}", file=archivo)
            
            await self._cleanup_dm(msg.channel)
            print(f"✅ [Backup] Enviado a {owner.name}")

        except Exception as e:
            print(f"❌ [Backup] Error: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))