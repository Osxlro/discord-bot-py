import logging
import discord
from discord import app_commands
from discord.ext import commands
from config import settings
from services.features import level_service
from services.core import db_service, lang_service
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
        
        embed = await level_service.get_rank_embed(ctx.guild, target, lang)
        
        if not embed:
            msg = lang_service.get_text("rank_no_data", lang)
            return await ctx.reply(embed=embed_service.warning(
                lang_service.get_text("title_info", lang), msg, lite=True
            ))

        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="leaderboard", description="Muestra el top de XP del servidor")
    async def leaderboard(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        rows = await db_service.fetch_all(
            f"SELECT user_id, level, xp, rebirths FROM guild_stats WHERE guild_id = ? ORDER BY rebirths DESC, level DESC, xp DESC LIMIT {settings.LEVELS_CONFIG['LEADERBOARD_LIMIT']}", 
            (ctx.guild.id,)
        )
        
        if not rows:
            msg = lang_service.get_text("leaderboard_empty", lang)
            await ctx.reply(embed=embed_service.info(lang_service.get_text("title_empty", lang), msg))
            return

        # Delegamos la construcción visual al servicio
        pages = level_service.get_leaderboard_pages(ctx.guild, rows, lang)

        if len(pages) == 1:
            await ctx.reply(embed=pages[0])
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            view.message = await ctx.reply(embed=pages[0], view=view)

    @commands.hybrid_command(name="rebirth", description="Reinicia tu nivel (requiere Nivel 100) para ganar un Rebirth.")
    async def rebirth(self, ctx: commands.Context):
        await ctx.defer()
        success, result = await db_service.do_rebirth(ctx.guild.id, ctx.author.id)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if success:
            msg = lang_service.get_text("rebirth_success", lang, rebirths=result)
            await ctx.send(embed=embed_service.success(lang_service.get_text("rebirth_title_success", lang), msg))
        else:
            if result == "no_data":
                msg = lang_service.get_text("rank_no_data", lang)
            elif isinstance(result, int):
                msg = lang_service.get_text("rebirth_fail_level", lang, level=result)
            else:
                msg = lang_service.get_text("rebirth_fail_generic", lang)
            
            await ctx.send(embed=embed_service.error(lang_service.get_text("rebirth_title_fail", lang), msg))

async def setup(bot: commands.Bot):
    await bot.add_cog(Niveles(bot))