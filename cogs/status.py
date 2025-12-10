import discord
from discord.ext import commands, tasks
from itertools import cycle
from config import settings

class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cargamos los estados desde la configuración
        self.config_presence = settings.CONFIG.get("presence", {})
        self.statuses = cycle(self.config_presence.get("statuses", []))
        
        # Iniciamos la tarea de bucle
        self.status_loop.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'✅ Módulo Status cargado.')

    def _get_activity_type(self, type_str: str) -> discord.ActivityType:
        """Convierte el texto del config a un objeto ActivityType de Discord."""
        type_str = type_str.lower()
        if type_str == "playing": return discord.ActivityType.playing
        if type_str == "watching": return discord.ActivityType.watching
        if type_str == "listening": return discord.ActivityType.listening
        if type_str == "competing": return discord.ActivityType.competing
        return discord.ActivityType.playing # Default

    # El bucle se repite cada X segundos (definidos en config)
    # Si no hay config, por defecto cada 30 segundos
    @tasks.loop(seconds=settings.CONFIG.get("presence", {}).get("rotate_interval", 30))
    async def status_loop(self):
        # Esperamos a que el bot esté totalmente listo antes de cambiar nada
        await self.bot.wait_until_ready()

        # Obtenemos el siguiente estado de la lista
        current_status = next(self.statuses)
        
        # Creamos el objeto Activity
        activity_type = self._get_activity_type(current_status["type"])
        activity = discord.Activity(
            type=activity_type, 
            name=current_status["text"]
        )

        # Aplicamos el cambio
        await self.bot.change_presence(activity=activity)

    # Si descargas el módulo (hot-reload), cancelamos el bucle para que no se duplique
    def cog_unload(self):
        self.status_loop.cancel()

async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))