import discord
from discord.ext import commands
from services import embed_service
from config import settings

class Bienvenidas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # EVENTO: Cuando alguien entra al servidor
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # 1. Obtener el canal desde la configuración
        channel_id = settings.CONFIG["channels"]["welcome_channel_id"]
        channel = self.bot.get_channel(channel_id)

        if not channel:
            print(f"❌ Error: No se encontró el canal de bienvenida (ID: {channel_id})")
            return

        # 2. Diseñar el Embed de bienvenida
        embed = embed_service.success(
            title=f"¡Bienvenido/a {member.name}!",
            description=f"Hola {member.mention}, gracias por unirte a **{member.guild.name}**. \n¡Esperamos que te diviertas!"
        )
        embed.set_thumbnail(url=member.display_avatar.url) # Pone la foto del usuario
        
        # 3. Enviar mensaje
        await channel.send(embed=embed)

    # EVENTO: Cuando alguien se va del servidor
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Usamos el mismo canal, o podrías configurar uno de "logs"
        channel_id = settings.CONFIG["channels"]["welcome_channel_id"]
        channel = self.bot.get_channel(channel_id)

        if channel:
            embed = embed_service.error(
                title="Un usuario ha partido",
                description=f"{member.name} ha abandonado el servidor. ¡Maldita rata!"
            )
            await channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Bienvenidas(bot))