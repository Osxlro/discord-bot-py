import discord
from discord.ext import commands
from config import settings
from services import embed_service
import datetime

class Logger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(self, embed: discord.Embed):
        """Función auxiliar para enviar al canal de logs."""
        channel_id = settings.CONFIG["channels"]["logs_channel_id"]
        # Si es 0 o no existe, no hacemos nada
        if not channel_id: 
            return
            
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed)

    # 1. Cuando se borra un mensaje
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot: return # Ignorar bots
        
        embed = embed_service.info("Mensaje Eliminado", f"**Autor:** {message.author.mention}\n**Canal:** {message.channel.mention}")
        embed.add_field(name="Contenido", value=message.content or "*(Sin contenido de texto)*", inline=False)
        embed.color = discord.Color.orange() # Sobrescribimos color a Naranja para alertas
        
        await self._send_log(embed)

    # 2. Cuando se edita un mensaje
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot: return
        if before.content == after.content: return # A veces discord dispara esto sin cambios reales

        embed = embed_service.info("Mensaje Editado", f"**Autor:** {before.author.mention}\n**Canal:** {before.channel.mention}")
        embed.add_field(name="Antes", value=before.content, inline=False)
        embed.add_field(name="Después", value=after.content, inline=False)
        
        await self._send_log(embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Logger(bot))