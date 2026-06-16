import discord
from discord.ext import commands
from services.utils import embed_service
from services.core import db_service, lang_service

class Mencion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def process_message_mention(self, message: discord.Message, lang: str, config: dict):
        if self.bot.user in message.mentions and len(message.content.split()) == 1 and not message.mention_everyone:
            respuesta = config.get('mention_response') or lang_service.get_text("mention_response_default", lang, bot=self.bot.user.name)
            await message.channel.send(embed=embed_service.info(lang_service.get_text("mention_title", lang), respuesta))

async def setup(bot: commands.Bot):
    await bot.add_cog(Mencion(bot))