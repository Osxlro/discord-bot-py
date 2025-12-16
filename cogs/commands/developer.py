import discord
from discord.ext import commands

class Developer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Comando de texto clásico: !sync
    @commands.command(name="sync")
    @commands.is_owner() # Descomenta esto si solo tú debes usarlo (requiere configurar owner_id)
    async def sync(self, ctx: commands.Context):
        """Sincroniza los comandos Slash manualmente."""
        
        # Mensaje de espera
        msg = await ctx.reply("⏳ Sincronizando árbol de comandos...", mention_author=False)
        
        try:
            # 1. Sincroniza con Discord
            synced = await self.bot.tree.sync()
            
            # 2. Confirma
            await msg.edit(content=f"✅ **¡Sincronización Completada!**\nSe han actualizado `{len(synced)}` comandos Slash globalmente.")
            print(f"Comandos sincronizados manualmente por {ctx.author}")
            
        except Exception as e:
            await msg.edit(content=f"❌ **Error al sincronizar:**\n`{e}`")

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
    await bot.add_cog(Developer(bot))