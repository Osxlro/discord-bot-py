# cogs/utils/mencion.py
import discord
from discord.ext import commands
from services import db_service, embed_service
from config import settings

class Mencion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # LOGICA MEJORADA:
        # 1. Verificamos si el bot está en la lista de mencionados.
        # 2. Verificamos que no sea un @everyone o @here.
        # 3. Verificamos que el mensaje no tenga más palabras (len == 1).
        if self.bot.user in message.mentions and len(message.content.split()) == 1 and not message.mention_everyone:
            
            # 1. Buscamos configuración en la DB
            row = await db_service.fetch_one("SELECT mention_response FROM guild_config WHERE guild_id = ?", (message.guild.id,))
            
            # 2. Definimos qué responder
            if row and row['mention_response']:
                respuesta = row['mention_response']
            else:
                prefix = settings.CONFIG["bot_config"]["prefix"]
                respuesta = f"¡Hola! Soy **{self.bot.user.name}**.\nUsa `/help` o `{prefix}help` para ver mis comandos."

            # 3. Enviamos el embed
            embed = embed_service.info("👋 ¿Me llamaste?", respuesta)
            await message.channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Mencion(bot))