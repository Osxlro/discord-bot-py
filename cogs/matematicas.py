# Archivo: cogs/matematicas.py
import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import math_service, embed_service

class Matematicas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Comando Único: /matematicas
    @app_commands.command(name="matematicas", description="Realiza operaciones matemáticas")
    @app_commands.describe(
        tipo="¿Qué operación quieres realizar?",
        num1="El primer número",
        num2="El segundo número"
    )
    async def matematicas(
        self, 
        interaction: discord.Interaction, 
        tipo: Literal["sumar", "restar", "multiplicacion", "division"], # Esto crea el menú desplegable
        num1: int, 
        num2: int
    ):
        try:
            # 1. Llamamos a la lógica (Service)
            resultado = math_service.calcular(tipo, num1, num2)
            
            # 2. Diseñamos la respuesta (Embed Service)
            # Añadimos un emoji según la operación para que se vea pro
            emojis = {
                "sumar": "➕", "restar": "➖", 
                "multiplicacion": "✖️", "division": "➗"
            }
            emoji_op = emojis.get(tipo, "🧮")
            
            embed = embed_service.success(
                title="Cálculo Completado",
                description=f"{emoji_op} La operación **{tipo}** de `{num1}` y `{num2}` es: **{resultado}**"
            )
            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            # Capturamos errores de lógica (como dividir por cero)
            embed = embed_service.error("Error Matemático", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Matematicas(bot))