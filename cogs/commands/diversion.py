import discord
from discord.ext import commands
from discord import app_commands
from services.features import diversion_service
from services.core import lang_service
from services.utils import embed_service

class Diversion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="jumbo", description="Muestra la imagen de un emoji en grande.")
    @app_commands.describe(emoji="Pon aquí el emoji personalizado")
    async def jumbo(self, ctx: commands.Context, emoji: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed, error = await diversion_service.handle_jumbo(emoji, lang)
        
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="coinflip", description="Lanza una moneda.")
    async def coinflip(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = diversion_service.handle_coinflip(lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="choice", description="Elige entre dos opciones.")
    async def eleccion(self, ctx: commands.Context, opcion_a: str, opcion_b: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = diversion_service.handle_choice(opcion_a, opcion_b, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="emojimix", description="Mezcla dos emojis.")
    async def emojimix(self, ctx: commands.Context, emoji1: str, emoji2: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = diversion_service.handle_emojimix(emoji1, emoji2, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="confess", description="Confesión anónima.")
    @app_commands.describe(secreto="Tu secreto.")
    async def confesar(self, ctx: commands.Context, *, secreto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        channel_id, embed, error = await diversion_service.handle_confess(ctx.guild.id if ctx.guild else None, secreto, lang)
        
        if error:
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
            
        canal = self.bot.get_channel(channel_id)
        if not canal: return

        try:
            await canal.send(embed=embed)
            msg = lang_service.get_text("confess_sent", lang, channel=canal.mention)
            await ctx.reply(embed=embed_service.success(lang_service.get_text("title_success", lang), msg, lite=True), ephemeral=True)
        except discord.Forbidden:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("confess_error_perms", lang), lite=True), ephemeral=True)

    @commands.hybrid_command(name="8ball", description="Pregúntale a la bola mágica.")
    @app_commands.describe(pregunta="Tu pregunta")
    async def eightball(self, ctx: commands.Context, pregunta: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        embed = diversion_service.handle_8ball(pregunta, lang)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Diversion(bot))