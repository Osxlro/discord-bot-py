import discord
from discord.ext import commands
from services import embed_service, db_service, lang_service

class Bienvenidas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        row = await db_service.fetch_one("SELECT welcome_channel_id FROM guild_config WHERE guild_id = ?", (member.guild.id,))
        if not row or not row['welcome_channel_id']: return
        
        channel = self.bot.get_channel(row['welcome_channel_id'])
        if channel:
            lang = await lang_service.get_guild_lang(member.guild.id)
            title = lang_service.get_text("welcome_title", lang, user=member.name)
            desc = lang_service.get_text("welcome_desc", lang, mention=member.mention, server=member.guild.name)
            await channel.send(embed=embed_service.success(title, desc, thumbnail=member.display_avatar.url))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        row = await db_service.fetch_one("SELECT welcome_channel_id, server_goodbye_msg FROM guild_config WHERE guild_id = ?", (member.guild.id,))
        if not row or not row['welcome_channel_id']: return

        channel = self.bot.get_channel(row['welcome_channel_id'])
        if channel:
            lang = await lang_service.get_guild_lang(member.guild.id)
            title = lang_service.get_text("goodbye_title", lang)
            
            if row['server_goodbye_msg']:
                desc = row['server_goodbye_msg'].replace("{user}", member.name).replace("{server}", member.guild.name)
            else:
                desc = lang_service.get_text("goodbye_desc", lang, user=member.name)
                
            await channel.send(embed=embed_service.error(title, desc))

async def setup(bot: commands.Bot):
    await bot.add_cog(Bienvenidas(bot))