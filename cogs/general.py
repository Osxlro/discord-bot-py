import discord
from discord.ext import commands
from discord import app_commands
from services import math_service  # Importamos nuestra lógica separada

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Evento cuando el Cog se carga
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Módulo General cargado.')

    # Comando Slash: /saludar
    @app_commands.command(name="saludar", description="Te saluda cordialmente")
    async def saludar(self, interaction: discord.Interaction):
        # Usamos la lógica del servicio, no procesamos nada aquí
        mensaje = math_service.obtener_saludo_personalizado(interaction.user.name)
        await interaction.response.send_message(mensaje)

    # TEST
    @app_commands.command(name="error_test", description="Comando para probar el manejador de errores")
    @app_commands.checks.has_permissions(administrator=True) # Requiere admin
    async def error_test(self, interaction: discord.Interaction):
        # Simulamos una división por cero
        resultado = 1 / 0 
        await interaction.response.send_message(f"Resultado: {resultado}")

    # Comando Slash: /sumar
    @app_commands.command(name="sumar", description="Suma dos números")
    @app_commands.describe(num1="El primer número", num2="El segundo número")
    async def sumar(self, interaction: discord.Interaction, num1: int, num2: int):
        # Delegamos el cálculo al servicio
        resultado = math_service.calcular_suma(num1, num2)
        await interaction.response.send_message(f"El resultado es: **{resultado}**")

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))