import discord
from discord.ext import commands
from services import embed_service, db_service

class Logger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(self, guild_id: int, embed: discord.Embed):
        """Busca el canal de logs en la DB y envía el embed."""
        row = await db_service.fetch_one("SELECT logs_channel_id FROM guild_config WHERE guild_id = ?", (guild_id,))
        
        if not row or not row['logs_channel_id']:
            return
            
        channel = self.bot.get_channel(row['logs_channel_id'])
        if channel:
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        
        embed = embed_service.info("Mensaje Eliminado", f"**Autor:** {message.author.mention}\n**Canal:** {message.channel.mention}")
        embed.add_field(name="Contenido", value=message.content or "*(Sin texto)*", inline=False)
        embed.color = discord.Color.orange()
        
        await self._send_log(message.guild.id, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild: return
        if before.content == after.content: return

        embed = embed_service.info("Mensaje Editado", f"**Autor:** {before.author.mention}\n**Canal:** {before.channel.mention}")
        embed.add_field(name="Antes", value=before.content, inline=False)
        embed.add_field(name="Después", value=after.content, inline=False)
        
        await self._send_log(before.guild.id, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Logger(bot))