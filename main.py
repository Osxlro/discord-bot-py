import discord
import asyncio
import logging
import pathlib 
from config import settings
from discord.ext import commands
from services import db_service

# --- CONFIGURACIÓN DE LOGS ---
data_dir = pathlib.Path("./data")
data_dir.mkdir(exist_ok=True)

handler = logging.FileHandler(filename=data_dir / 'discord.log', encoding='utf-8', mode='w')
discord.utils.setup_logging(handler=handler, level=logging.INFO)

# Configuración de Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# --- LÓGICA DE PREFIX DINÁMICO ---
async def get_prefix(bot, message):
    if not message.guild:
        return settings.CONFIG["bot_config"]["prefix"]
    try:
        row = await db_service.fetch_one("SELECT custom_prefix FROM users WHERE user_id = ?", (message.author.id,))
        if row and row['custom_prefix']:
            return row['custom_prefix']
    except:
        pass
    return settings.CONFIG["bot_config"]["prefix"]

class BotPersonal(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=get_prefix, 
            intents=intents,
            help_command=None,
            activity=discord.Game(name="Iniciando sistemas...")
        )

    async def setup_hook(self):
        print("--- ⚙️  CARGANDO EXTENSIONES (PATHLIB) ---")
        
        # Usamos pathlib para recorrer la carpeta cogs de forma recursiva (rglob)
        # Esto funciona perfecto en Windows, Linux y Mac sin trucos raros.
        cogs_dir = pathlib.Path("./cogs")
        
        for file in cogs_dir.rglob("*.py"):
            # Ignoramos archivos __init__.py si existen
            if file.name == "__init__.py": continue
            
            # Convertimos la ruta de archivo a formato de punto (cogs.commands.general)
            # parts separa la ruta en ('cogs', 'commands', 'general.py')
            # [:-3] quita el .py del nombre final
            extension_name = ".".join(file.parts).replace(".py", "")
            
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
        try:
            await bot.start(settings.TOKEN)
        finally:
            print("--- 🛑 APAGANDO SERVICIOS ---")
            await db_service.close_db()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Apagando bot...")