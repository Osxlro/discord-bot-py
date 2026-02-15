import discord
import logging
from discord.ext import commands
from services.utils import embed_service
from config import settings
from services.core import db_service, lang_service

logger = logging.getLogger(__name__)

class Logger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(self, guild_id: int, embed: discord.Embed):
        """Busca el canal de logs en la DB y envía el embed."""
        config = await db_service.get_guild_config(guild_id)
        channel_id = config.get('logs_channel_id')
        
        if not channel_id:
            return
            
        try:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)
        except Exception:
            logger.exception(f"Error enviando log al servidor {guild_id}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        lang = await lang_service.get_guild_lang(message.guild.id)
        
        author_lbl = lang_service.get_text("log_field_author", lang)
        channel_lbl = lang_service.get_text("log_field_channel", lang)
        
        embed = embed_service.info(lang_service.get_text("log_msg_deleted", lang), f"{author_lbl} {message.author.mention}\n{channel_lbl} {message.channel.mention}")
        embed.add_field(name=lang_service.get_text("log_field_content", lang), value=message.content or lang_service.get_text("log_no_content", lang), inline=False)
        embed.color = settings.COLORS["ORANGE"]
        
        await self._send_log(message.guild.id, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild: return
        if before.content == after.content: return
        lang = await lang_service.get_guild_lang(before.guild.id)

        author_lbl = lang_service.get_text("log_field_author", lang)
        channel_lbl = lang_service.get_text("log_field_channel", lang)

        embed = embed_service.info(lang_service.get_text("log_msg_edited", lang), f"{author_lbl} {before.author.mention}\n{channel_lbl} {before.channel.mention}")
        embed.add_field(name=lang_service.get_text("log_field_before", lang), value=before.content, inline=False)
        embed.add_field(name=lang_service.get_text("log_field_after", lang), value=after.content, inline=False)
        
        await self._send_log(before.guild.id, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        lang = await lang_service.get_guild_lang(guild.id)
        user_lbl = lang_service.get_text("log_field_user", lang)
        embed = embed_service.error(lang_service.get_text("log_user_banned", lang), f"{user_lbl} {user.mention} (`{user.id}`)")
        embed.set_thumbnail(url=user.display_avatar.url)
        await self._send_log(guild.id, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        lang = await lang_service.get_guild_lang(guild.id)
        user_lbl = lang_service.get_text("log_field_user", lang)
        embed = embed_service.success(lang_service.get_text("log_user_unbanned", lang), f"{user_lbl} {user.mention} (`{user.id}`)")
        embed.set_thumbnail(url=user.display_avatar.url)
        await self._send_log(guild.id, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot: return
        lang = await lang_service.get_guild_lang(after.guild.id)
        user_lbl = lang_service.get_text("log_field_user", lang)
        
        # Cambio de Nick
        if before.nick != after.nick:
            embed = embed_service.info(lang_service.get_text("log_nick_change", lang), f"{user_lbl} {after.mention}")
            embed.add_field(name=lang_service.get_text("log_field_before", lang), value=before.nick or lang_service.get_text("log_none", lang), inline=True)
            embed.add_field(name=lang_service.get_text("log_field_after", lang), value=after.nick or lang_service.get_text("log_none", lang), inline=True)
            embed.set_thumbnail(url=after.display_avatar.url)
            await self._send_log(after.guild.id, embed)

        # Cambio de Roles
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            
            roles_lbl = lang_service.get_text("log_field_roles", lang)

            if added:
                roles_str = ", ".join([r.mention for r in added])
                embed = embed_service.success(lang_service.get_text("log_roles_added", lang), f"{user_lbl} {after.mention}\n**{roles_lbl}:** {roles_str}")
                await self._send_log(after.guild.id, embed)
            
            if removed:
                roles_str = ", ".join([r.mention for r in removed])
                embed = embed_service.error(lang_service.get_text("log_roles_removed", lang), f"{user_lbl} {after.mention}\n**{roles_lbl}:** {roles_str}")
                await self._send_log(after.guild.id, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Logger(bot))