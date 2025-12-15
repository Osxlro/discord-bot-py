import discord
import datetime
from discord.ext import commands
from services import random_service, embed_service, db_service, lang_service

class Chaos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return

        config = await db_service.fetch_one("SELECT chaos_enabled, chaos_probability FROM guild_config WHERE guild_id = ?", (message.guild.id,))
        enabled = config['chaos_enabled'] if config else 1
        prob = config['chaos_probability'] if config else 0.01

        if not enabled: return
        if random_service.verificar_suerte(prob):
            try:
                lang = await lang_service.get_guild_lang(message.guild.id)
                await message.author.timeout(datetime.timedelta(minutes=1), reason="Chaos")
                
                txt = lang_service.get_text("chaos_bang", lang, user=message.author.name, prob=int(prob*100))
                await message.channel.send(embed=embed_service.info("🔫 Bang!", txt))
            except: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Chaos(bot))