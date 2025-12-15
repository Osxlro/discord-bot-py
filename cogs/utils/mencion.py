import discord
from discord.ext import commands
from services import db_service, embed_service, lang_service

class Mencion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        if self.bot.user in message.mentions and len(message.content.split()) == 1 and not message.mention_everyone:
            
            row = await db_service.fetch_one("SELECT mention_response FROM guild_config WHERE guild_id = ?", (message.guild.id,))
            lang = await lang_service.get_guild_lang(message.guild.id)
            
            respuesta = row['mention_response'] if row and row['mention_response'] else lang_service.get_text("mention_response_default", lang, bot=self.bot.user.name)
            await message.channel.send(embed=embed_service.info("👋 Hello", respuesta))

async def setup(bot: commands.Bot):
    await bot.add_cog(Mencion(bot))