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
        """
        Función interna para limpiar backups viejos del DM.
        Mantiene los 3 más recientes y borra el resto.
        """
        backups_encontrados = []
        
        # Buscamos en el historial (últimos 100 mensajes para asegurar)
        async for message in channel.history(limit=100):
            # Criterio: Mensaje del bot + Tiene archivo adjunto + Dice "Backup" o es .sqlite3
            es_mio = message.author.id == self.bot.user.id
            tiene_archivo = len(message.attachments) > 0
            es_backup = "Backup" in message.content or (tiene_archivo and message.attachments[0].filename.endswith(".sqlite3"))
            
            if es_mio and es_backup:
                backups_encontrados.append(message)

        # Si hay más de 3 backups, borramos los antiguos
        # (history ya devuelve de más nuevo a más viejo por defecto)
        if len(backups_encontrados) > 3:
            papelera = backups_encontrados[3:] # Del cuarto en adelante
            
            for msg in papelera:
                try:
                    await msg.delete()
                    await asyncio.sleep(1) # Evitar rate limits
                except Exception:
                    pass
            
            print(f"🧹 [Backup] Se eliminaron {len(papelera)} backups antiguos del DM.")

    # --- TAREA AUTOMÁTICA (Cada 24h) ---
    @tasks.loop(hours=24)
    async def backup_db(self):
        await self.bot.wait_until_ready()
        db_path = os.path.join(settings.BASE_DIR, "data", "database.sqlite3")
        
        if not os.path.exists(db_path):
            return

        try:
            app_info = await self.bot.application_info()
            owner = app_info.owner
            
            # Formato de fecha
            fecha = datetime.date.today().strftime("%Y-%m-%d")
            
            # Enviar el nuevo backup
            archivo = discord.File(db_path, filename=f"backup_{fecha}.sqlite3")
            msg = await owner.send(content=f"📦 **Backup** {fecha}", file=archivo)
            
            # --- LIMPIEZA AUTOMÁTICA ---
            # Usamos el canal del mensaje que acabamos de enviar
            await self._cleanup_dm(msg.channel)

        except Exception as e:
            print(f"❌ [Backup] Error: {e}")

    # --- COMANDO MANUAL (Por si quieres limpiar ahora) ---
    @commands.command(name="limpiar_backups", hidden=True)
    @commands.is_owner()
    async def manual_cleanup(self, ctx: commands.Context):
        """Fuerza la limpieza de backups en tu DM."""
        await ctx.message.add_reaction("⏳")
        
        # Obtenemos el canal DM contigo
        dm_channel = await ctx.author.create_dm()
        await self._cleanup_dm(dm_channel)
        
        await ctx.message.add_reaction("✅")
        await ctx.reply("🧹 Limpieza de DM completada (Se mantuvieron los últimos 3).", delete_after=5)

async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))