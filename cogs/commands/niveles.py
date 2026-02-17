import logging
import discord
from discord import app_commands
from discord.ext import commands
from services.features import level_service
from services.core import lang_service
from services.utils import embed_service, pagination_service

logger = logging.getLogger(__name__)

class Niveles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="rank", description="Muestra el nivel, progreso y rebirths de un usuario.")
    @app_commands.describe(usuario="El usuario a consultar")
    async def rank(self, ctx: commands.Context, usuario: discord.Member = None):
        target = usuario or ctx.author
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        embed = await level_service.handle_rank(ctx.guild, target, lang)
        
        if not embed:
            msg = lang_service.get_text("rank_no_data", lang)
            return await ctx.reply(embed=embed_service.warning(
                lang_service.get_text("title_info", lang), msg, lite=True
            ))

        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="leaderboard", description="Muestra el top de XP del servidor")
    async def leaderboard(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        pages = await level_service.handle_leaderboard(ctx.guild, lang)

        if not pages:
            msg = lang_service.get_text("leaderboard_empty", lang)
            await ctx.reply(embed=embed_service.info(lang_service.get_text("title_empty", lang), msg))
            return

        if len(pages) == 1:
            await ctx.reply(embed=pages[0])
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.reply(embed=pages[0], view=view)

    @commands.hybrid_command(name="rebirth", description="Reinicia tu nivel (requiere Nivel 100) para ganar un Rebirth.")
    async def rebirth(self, ctx: commands.Context):
        await ctx.defer()
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed, _ = await level_service.handle_rebirth(ctx.guild.id, ctx.author.id, lang)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Niveles(bot))