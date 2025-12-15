import discord
import datetime
from discord.ext import commands
from services import random_service, embed_service, db_service # Importamos db_service

class Chaos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # 1. Obtener configuración de la DB
        config = await db_service.fetch_one("SELECT chaos_enabled, chaos_probability FROM guild_config WHERE guild_id = ?", (message.guild.id,))
        
        # Si no hay config, asumimos valores por defecto (Activado, 1%)
        enabled = config['chaos_enabled'] if config else 1
        probabilidad = config['chaos_probability'] if config else 0.01

        # Si está desactivado, no hacemos nada
        if not enabled:
            return

        # 2. Verificar suerte
        if random_service.verificar_suerte(probabilidad):
            try:
                # 3. Aplicar Timeout (1 minuto fijo por ahora)
                tiempo = datetime.timedelta(minutes=1)
                await message.author.timeout(tiempo, reason="🔫 Ruleta Rusa: ¡Mala suerte!")

                # 4. Notificar
                porcentaje = int(probabilidad * 100)
                embed = embed_service.info(
                    "🔫 ¡Bang!",
                    f"¡Pum! **{message.author.name}** ha tenido mala suerte (probabilidad: {porcentaje}%).\nEstarás aislado por 1 minuto."
                )
                await message.channel.send(embed=embed)

            except discord.Forbidden:
                # El bot no tiene permisos o el usuario es admin
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Chaos(bot))