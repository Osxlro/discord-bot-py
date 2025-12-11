import discord
from discord.ext import commands
from services import embed_service, db_service # Importamos db_service

class Bienvenidas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # 1. Consultar DB
        row = await db_service.fetch_one("SELECT welcome_channel_id FROM guild_config WHERE guild_id = ?", (member.guild.id,))
        
        if not row or not row['welcome_channel_id']:
            return # No hay canal configurado

        channel = self.bot.get_channel(row['welcome_channel_id'])
        if channel:
            embed = embed_service.success(
                title=f"¡Bienvenido/a {member.name}!",
                description=f"Hola {member.mention}, gracias por unirte a **{member.guild.name}**."
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # 1. Consultar DB
        row = await db_service.fetch_one("SELECT welcome_channel_id FROM guild_config WHERE guild_id = ?", (member.guild.id,))
        
        if not row or not row['welcome_channel_id']:
            return

        channel = self.bot.get_channel(row['welcome_channel_id'])
        if channel:
            embed = embed_service.error(
                title="Un usuario ha partido",
                description=f"{member.name} ha abandonado el servidor."
            )
            await channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Bienvenidas(bot))