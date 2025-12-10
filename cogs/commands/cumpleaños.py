import discord
from discord.ext import commands
from discord import app_commands
from services import db_service, embed_service
import datetime

class Cumpleanos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="cumple", description="Sistema de cumpleaños")
    async def cumple(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @cumple.command(name="establecer", description="Guarda tu fecha de cumpleaños")
    @app_commands.describe(dia="Día (1-31)", mes="Mes (1-12)")
    async def establecer(self, ctx: commands.Context, dia: int, mes: int):
        # 1. Validaciones básicas
        try:
            # Intentamos crear una fecha para ver si es válida (ej: 30 de Febrero daría error)
            fecha_obj = datetime.date(2000, mes, dia) # Usamos año bisiesto 2000 por si cumple el 29 feb
            fecha_str = f"{dia}/{mes}"
        except ValueError:
            await ctx.reply(embed=embed_service.error("Fecha Inválida", "Esa fecha no existe en el calendario."), ephemeral=True)
            return

        # 2. Guardar en Base de Datos
        # Usamos INSERT OR REPLACE para guardar o actualizar si ya existía
        await db_service.execute(
            "INSERT OR REPLACE INTO users (user_id, birthday) VALUES (?, ?)",
            (ctx.author.id, fecha_str)
        )

        embed = embed_service.success(
            "¡Fecha Guardada!", 
            f"He guardado tu cumpleaños el día: **{fecha_str}** 🎂"
        )
        await ctx.reply(embed=embed)

    @cumple.command(name="ver", description="Mira el cumpleaños de alguien")
    async def ver(self, ctx: commands.Context, usuario: discord.Member = None):
        usuario = usuario or ctx.author
        
        # 3. Consultar Base de Datos
        data = await db_service.fetch_one("SELECT birthday FROM users WHERE user_id = ?", (usuario.id,))

        if data and data['birthday']:
            embed = embed_service.info(
                f"Cumpleaños de {usuario.name}",
                f"🎉 Su cumpleaños es el: **{data['birthday']}**"
            )
        else:
            msg = "No has configurado tu cumpleaños." if usuario == ctx.author else f"{usuario.name} no ha configurado su cumpleaños."
            embed = embed_service.error("No encontrado", msg)
            
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Cumpleanos(bot))