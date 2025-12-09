import discord
import os
import asyncio
from discord.ext import commands
from config import settings

# Configuración de Intents (Permisos)
intents = discord.Intents.default()
intents.message_content = True # Necesario si vas a leer mensajes

class BotPersonal(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None # Desactivamos el help por defecto para crear uno propio luego
        )

    async def setup_hook(self):
        """Este método se ejecuta al iniciar, ideal para cargar extensiones."""
        print("--- Cargando extensiones ---")
        # Recorre la carpeta cogs y carga los archivos .py
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'Extensión cargada: {filename}')
        
        # Sincronizar comandos con Discord (Importante para que aparezca el menu /)
        # NOTA: En producción, evita hacer sync global cada vez que reinicias.
        print("--- Sincronizando árbol de comandos ---")
        await self.tree.sync() 
        print("--- Sincronización completada ---")

    async def on_ready(self):
        print(f'Conectado como {self.user} (ID: {self.user.id})')
        print('Bot listo para operar.')

async def main():
    bot = BotPersonal()
    async with bot:
        await bot.start(settings.TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Manejo limpio de cierre (Ctrl+C)
        print("Apagando bot...")