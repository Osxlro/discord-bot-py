import discord
import datetime
from discord.ext import commands
from config import settings
from services import random_service, embed_service

class Chaos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Ignorar bots y mensajes privados
        if message.author.bot or not message.guild:
            return

        # 2. Obtener configuración (Si no existe en config, asume 0/Apagado)
        # Se espera un valor decimal: 0.01 = 1%
        probabilidad = settings.CONFIG.get("chaos_config", {}).get("roulette_chance", 0.0)

        # 3. Verificar suerte usando el servicio
        if random_service.verificar_suerte(probabilidad):
            try:
                # 4. Aplicar Timeout (1 minuto)
                tiempo = datetime.timedelta(minutes=1)
                await message.author.timeout(tiempo, reason="🔫 Ruleta Rusa: ¡Mala suerte!")

                # 5. Notificar
                embed = embed_service.info(
                    "🔫 ¡Bang!",
                    f"¡Pum! **{message.author.name}** ha tenido mala suerte y estará aislado por 1 minuto."
                )
                await message.channel.send(embed=embed)

            except discord.Forbidden:
                # El bot no tiene permisos o el usuario es admin/dueño
                print(f"⚠️ Chaos: No pude aislar a {message.author.name} (Faltan permisos o jerarquía).")

async def setup(bot: commands.Bot):
    await bot.add_cog(Chaos(bot))