import discord
import os
import asyncio
import logging

from config import settings
from discord.ext import commands
from services import db_service

# --- CONFIGURACIÓN DE LOGS ---
# Esto guardará todo lo que pase en un archivo 'discord.log' y lo mostrará en consola
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
discord.utils.setup_logging(handler=handler, level=logging.INFO)

# Configuración de Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class BotPersonal(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=settings.CONFIG["bot_config"]["prefix"], 
            intents=intents,
            help_command=None,
            activity=discord.Game(name="Iniciando sistemas...") # Status inicial
        )

    async def setup_hook(self):
        print("--- ⚙️  CARGANDO EXTENSIONES ---")
        
        # os.walk recorre el árbol de directorios
        # root: la carpeta actual (ej: ./cogs/commands)
        # dirs: carpetas dentro
        # files: archivos dentro
        for root, dirs, files in os.walk('./cogs'):
            for filename in files:
                if filename.endswith('.py'):
                    # Construimos la ruta de importación tipo: cogs.commands.general
                    # 1. Quitamos './' del inicio y reemplazamos las barras de carpeta por puntos
                    relative_path = os.path.relpath(root, '.').replace(os.path.sep, '.')
                    extension_name = f"{relative_path}.{filename[:-3]}"
                    
                    try:
                        await self.load_extension(extension_name)
                        print(f'✅ Extensión cargada: {extension_name}')
                    except Exception as e:
                        print(f'❌ Error cargando {extension_name}: {e}')
        
        print("--- 💾 INICIANDO BASE DE DATOS ---")
        await db_service.init_db()

        print("--- 🔄 SINCRONIZANDO COMANDOS ---")
        try:
            synced = await self.tree.sync()
            print(f"✨ Se han sincronizado {len(synced)} comandos Slash.")
        except Exception as e:
            print(f"❌ Error al sincronizar: {e}")

    async def on_ready(self):
        print(f'------------------------------------')
        print(f'🤖 Bot conectado: {self.user}')
        print(f'🆔 ID: {self.user.id}')
        print(f'------------------------------------')
        settings.set_bot_icon(self.user.display_avatar.url)

async def main():
    bot = BotPersonal()
    async with bot:
        await bot.start(settings.TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Apagando bot...")