import discord
from discord.ext import commands
from services import embed_service, db_service, lang_service

class Bienvenidas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Optimizamos usando el caché de configuración en lugar de consulta directa
        config = await db_service.get_guild_config(member.guild.id)
        channel_id = config.get('welcome_channel_id')
        if not channel_id: return
        
        channel = self.bot.get_channel(channel_id)
        if channel:
            lang = await lang_service.get_guild_lang(member.guild.id)
            title = lang_service.get_text("welcome_title", lang, user=member.name)
            desc = lang_service.get_text("welcome_desc", lang, mention=member.mention, server=member.guild.name)
            
            # Corregimos el error: success() no acepta 'thumbnail'. Lo añadimos manualmente al objeto embed.
            embed = embed_service.success(title, desc)
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = await db_service.get_guild_config(member.guild.id)
        channel_id = config.get('welcome_channel_id')
        if not channel_id: return

        channel = self.bot.get_channel(channel_id)
        if channel:
            lang = await lang_service.get_guild_lang(member.guild.id)
            title = lang_service.get_text("goodbye_title", lang)
            
            goodbye_msg = config.get('server_goodbye_msg')
            if goodbye_msg:
                desc = goodbye_msg.replace("{user}", member.name).replace("{server}", member.guild.name)
            else:
                desc = lang_service.get_text("goodbye_desc", lang, user=member.name)
                
            await channel.send(embed=embed_service.error(title, desc))

async def setup(bot: commands.Bot):
    await bot.add_cog(Bienvenidas(bot))