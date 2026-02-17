import discord
from discord.ext import commands
from typing import Literal
from services.features import birthday_service
from services.core import lang_service
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
        embed, error = await birthday_service.handle_establish_birthday(ctx.author.id, dia, mes, lang)
        
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error), ephemeral=True)
        await ctx.reply(embed=embed)

    @cumple.command(name="delete", description= "Elimina tu cumpleaños, o el de alguien más.")
    async def eliminar(self, ctx: commands.Context, usuario: discord.Member = None):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        target = usuario or ctx.author
        if target.id != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("error_no_perms", lang)), ephemeral=True)

        embed = await birthday_service.handle_delete_birthday(target.id, lang)
        await ctx.reply(embed=embed)

    @cumple.command(name="privacy", description="Decide si festejar tu cumpleaños o no.")
    async def privacidad(self, ctx: commands.Context, estado: Literal["Visible", "Oculto"]):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = 1 if estado == "Visible" else 0
        
        embed = await birthday_service.handle_privacy_update(ctx.author.id, val, lang)
        await ctx.reply(embed=embed)

    @cumple.command(name="list", description="Revisa la lista de próximos cumpleaños.")
    async def lista(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await birthday_service.handle_get_upcoming_list(ctx.guild, lang)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Cumpleanos(bot))