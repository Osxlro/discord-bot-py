import discord
from discord.ext import commands
from typing import Literal
from services.features import birthday_service
import datetime

from services.core import db_service, lang_service
from services.utils import embed_service

class Cumpleanos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="birthday", description="Comandos relacionados con cumpleaños.")
    async def cumple(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @cumple.command(name="establish", description="Establece tu cumpleaños.")
    async def establecer(self, ctx: commands.Context, dia: int, mes: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        try:
            datetime.date(2000, mes, dia)
            fecha = f"{dia}/{mes}"
            await db_service.execute(
                "INSERT INTO users (user_id, birthday, celebrate) VALUES (?, ?, 1) "
                "ON CONFLICT(user_id) DO UPDATE SET birthday = excluded.birthday, celebrate = 1",
                (ctx.author.id, fecha)
            )
            msg = lang_service.get_text("bday_saved", lang, date=fecha)
            await ctx.reply(embed=embed_service.success(lang_service.get_text("title_success", lang), msg))
        except ValueError:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("bday_invalid", lang)), ephemeral=True)

    @cumple.command(name="delete", description= "Elimina tu cumpleaños, o el de alguien más.")
    async def eliminar(self, ctx: commands.Context, usuario: discord.Member = None):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        target = usuario or ctx.author
        if target.id != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("error_no_perms", lang)), ephemeral=True)

        await db_service.execute("UPDATE users SET birthday = NULL WHERE user_id = ?", (target.id,))
        await ctx.reply(embed=embed_service.success(lang_service.get_text("title_success", lang), lang_service.get_text("bday_removed", lang)))

    @cumple.command(name="privacy", description="Decide si festejar tu cumpleaños o no.")
    async def privacidad(self, ctx: commands.Context, estado: Literal["Visible", "Oculto"]):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = 1 if estado == "Visible" else 0
        await db_service.execute("UPDATE users SET celebrate = ? WHERE user_id = ?", (val, ctx.author.id))
        msg = lang_service.get_text("bday_visible" if val else "bday_hidden", lang)
        await ctx.reply(embed=embed_service.success(lang_service.get_text("bday_privacy", lang), msg))

    @cumple.command(name="list", description="Revisa la lista de próximos cumpleaños.")
    async def lista(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await birthday_service.get_upcoming_birthdays_embed(ctx.guild, lang)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Cumpleanos(bot))