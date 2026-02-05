import discord
from discord.ext import commands
from services import embed_service, db_service, lang_service

class Logger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(self, guild_id: int, embed: discord.Embed):
        """Busca el canal de logs en la DB y envía el embed."""
        config = await db_service.get_guild_config(guild_id)
        channel_id = config.get('logs_channel_id')
        
        if not channel_id:
            return
            
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        lang = await lang_service.get_guild_lang(message.guild.id)
        
        embed = embed_service.info(lang_service.get_text("log_msg_deleted", lang), f"**Autor:** {message.author.mention}\n**Canal:** {message.channel.mention}")
        embed.add_field(name="Contenido", value=message.content or lang_service.get_text("log_no_content", lang), inline=False)
        embed.color = discord.Color.orange()
        
        await self._send_log(message.guild.id, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild: return
        if before.content == after.content: return
        lang = await lang_service.get_guild_lang(before.guild.id)

        embed = embed_service.info(lang_service.get_text("log_msg_edited", lang), f"**Autor:** {before.author.mention}\n**Canal:** {before.channel.mention}")
        embed.add_field(name="Antes", value=before.content, inline=False)
        embed.add_field(name="Después", value=after.content, inline=False)
        
        await self._send_log(before.guild.id, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        lang = await lang_service.get_guild_lang(guild.id)
        embed = embed_service.error(lang_service.get_text("log_user_banned", lang), f"**Usuario:** {user.mention} (`{user.id}`)")
        embed.set_thumbnail(url=user.display_avatar.url)
        await self._send_log(guild.id, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        lang = await lang_service.get_guild_lang(guild.id)
        embed = embed_service.success(lang_service.get_text("log_user_unbanned", lang), f"**Usuario:** {user.mention} (`{user.id}`)")
        embed.set_thumbnail(url=user.display_avatar.url)
        await self._send_log(guild.id, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot: return
        lang = await lang_service.get_guild_lang(after.guild.id)
        
        # Cambio de Nick
        if before.nick != after.nick:
            embed = embed_service.info(lang_service.get_text("log_nick_change", lang), f"**Usuario:** {after.mention}")
            embed.add_field(name="Antes", value=before.nick or lang_service.get_text("log_none", lang), inline=True)
            embed.add_field(name="Después", value=after.nick or lang_service.get_text("log_none", lang), inline=True)
            embed.set_thumbnail(url=after.display_avatar.url)
            await self._send_log(after.guild.id, embed)

        # Cambio de Roles
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            
            if added:
                roles_str = ", ".join([r.mention for r in added])
                embed = embed_service.success(lang_service.get_text("log_roles_added", lang), f"**Usuario:** {after.mention}\n**Roles:** {roles_str}")
                await self._send_log(after.guild.id, embed)
            
            if removed:
                roles_str = ", ".join([r.mention for r in removed])
                embed = embed_service.error(lang_service.get_text("log_roles_removed", lang), f"**Usuario:** {after.mention}\n**Roles:** {roles_str}")
                await self._send_log(after.guild.id, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Logger(bot))