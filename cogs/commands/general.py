import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import embed_service, translator_service, math_service, lang_service

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(name="Traducir", callback=self.traducir_mensaje)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.hybrid_command(name="ping", description="Chequea el Ping del Bot.")
    async def ping(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        ms = round(self.bot.latency * 1000)
        
        txt = lang_service.get_text("ping_msg", lang, ms=ms)
        await ctx.reply(embed=embed_service.info("Ping", txt))

    @commands.hybrid_command(name="calc",description="Calculadora maestra")
    async def calc(self, ctx: commands.Context, operacion: Literal["sumar", "restar", "multiplicacion", "division"], num1: int, num2: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        emojis = {"sumar": "+", "restar": "-", "multiplicacion": "*", "division": "/"}
        
        try:
            res = math_service.calcular(operacion, num1, num2)
            txt = lang_service.get_text("calc_result", lang, a=num1, op=emojis[operacion], b=num2, res=res)
            await ctx.reply(embed=embed_service.success("Math", txt))
        except ValueError as e:
            txt = lang_service.get_text("calc_error", lang, error=str(e))
            await ctx.reply(embed=embed_service.error("Error", txt, lite=True))

    async def traducir_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        # Nota: Aquí usamos interacción directa, así que obtenemos el idioma manualmente
        lang = await lang_service.get_guild_lang(interaction.guild_id)
        await interaction.response.defer(ephemeral=True)
        
        try:
            res = await translator_service.traducir(message.content, "es")
            txt = lang_service.get_text("trans_result", lang, orig=message.content[:50]+"...", trans=res['traducido'])
            await interaction.followup.send(embed=embed_service.success("Traducir", txt), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))