import discord
from discord.ext import commands, tasks
import os
import datetime
from config import settings
# Nota: Backup es para el dueño, podríamos dejarlo en español o usar el default_lang (es).
# Usaremos 'es' hardcoded o default porque no depende de un servidor, es MD.

class Backup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backup_db.start()

    def cog_unload(self):
        self.backup_db.cancel()

    @tasks.loop(hours=24)
    async def backup_db(self):
        await self.bot.wait_until_ready()
        db_path = os.path.join(settings.BASE_DIR, "data", "database.sqlite3")
        if not os.path.exists(db_path): return

        try:
            app_info = await self.bot.application_info()
            owner = app_info.owner
            fecha = datetime.date.today().strftime("%Y-%m-%d")
            
            archivo = discord.File(db_path, filename=f"backup_{fecha}.sqlite3")
            # Texto simple ya que es admin
            await owner.send(content=f"📦 **Backup** {fecha}", file=archivo)
        except Exception as e:
            print(f"Backup Error: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))