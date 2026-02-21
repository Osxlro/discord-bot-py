import asyncio
import logging
import logging.handlers
import pathlib
import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from services.features import music_service
from services.core import db_service

# --- CONFIGURACIÓN DE LOGS ---
data_dir = pathlib.Path("./data")
data_dir.mkdir(exist_ok=True)

# Limpiar logs antiguos al reiniciar
for log_file in data_dir.glob("discord.log*"):
    try: log_file.unlink()
    except: pass

discord.utils.setup_logging(level=logging.INFO)
file_handler = logging.handlers.RotatingFileHandler(filename=data_dir / 'discord.log', encoding='utf-8', maxBytes=5*1024*1024, backupCount=5)
logging.getLogger().addHandler(file_handler)

logger = logging.getLogger("bot")

# Configuración de Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# --- LÓGICA DE PREFIX DINÁMICO ---
async def get_prefix(bot, message):
    # Permite que cada usuario tenga su propio prefijo si así lo desea,
    # de lo contrario usa el prefijo global definido en settings.
    if not message.guild:
        return settings.CONFIG["bot_config"]["prefix"]
    try:
        custom = await db_service.get_user_prefix(message.author.id)
        if custom: return custom
    except Exception:
        logger.exception("Error obteniendo prefijo dinámico")
    return settings.CONFIG["bot_config"]["prefix"]

class BotPersonal(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.playing, 
                name="Iniciando sistemas...",
                assets={'large_image': settings.CONFIG["bot_config"]["presence_asset"]}
            )
        )
        # Cooldown Global: 1 comando cada 3.0 segundos por usuario
        self.global_cd = commands.CooldownMapping.from_cooldown(1, 3.0, commands.BucketType.user)

    async def setup_hook(self):
        """Configuración inicial del bot en orden lógico."""
        # 1. Base de Datos: Debe estar lista antes de cargar cualquier lógica.
        await self._init_database()
        
        # 1.5 Registrar chequeos globales (Cooldowns)
        self.add_check(self.check_global_cooldown)
        self.tree.interaction_check = self.check_global_interaction

        # 2. Extensiones: Carga todos los Cogs (comandos, eventos, tareas).
        await self._load_extensions()

        # 3. Sincronización: Registra los Slash Commands en la API de Discord.
        await self._sync_commands()

    async def check_global_cooldown(self, ctx):
        """Verifica el cooldown global para comandos de prefijo."""
        # Los dueños del bot ignoran el cooldown
        if await self.is_owner(ctx.author): return True
        
        bucket = self.global_cd.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.user)
        return True

    async def check_global_interaction(self, interaction: discord.Interaction) -> bool:
        """Verifica el cooldown global para Slash Commands."""
        if await self.is_owner(interaction.user): return True

        # Adaptador: Creamos un objeto dummy porque CooldownMapping espera un mensaje con atributo .author
        class MockMsg:
            def __init__(self, u): self.author = u
            
        bucket = self.global_cd.get_bucket(MockMsg(interaction.user))
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise app_commands.CommandOnCooldown(bucket, retry_after)
        return True

    async def _init_database(self):
        logger.info("--- 💾 INICIANDO BASE DE DATOS ---")
        await db_service.init_db()

    async def _load_extensions(self):
        logger.info("--- ⚙️  CARGANDO EXTENSIONES ---")
        cogs_dir = pathlib.Path("./cogs")
        
        for file in cogs_dir.rglob("*.py"):
            if file.name == "__init__.py": continue
            
            extension_name = ".".join(file.parts).replace(".py", "")
            try:
                await self.load_extension(extension_name)
                logger.info(f'✅ Extensión cargada: {extension_name}')
            except Exception:
                logger.exception(f'❌ Error cargando {extension_name}')

    async def _sync_commands(self):
        logger.info("--- 🔄 SINCRONIZANDO COMANDOS ---")
        try:
            synced = await self.tree.sync()
            logger.info(f"✨ Se han sincronizado {len(synced)} comandos.")
        except Exception as e:
            logger.error(f"❌ Error al sincronizar: {e}")

    async def on_ready(self):
        logger.info('------------------------------------')
        logger.info(f'🤖 Bot conectado: {self.user}')
        logger.info(f'🆔 ID: {self.user.id}')
        logger.info('------------------------------------')
        settings.set_bot_icon(self.user.display_avatar.url)
        
        # Intentar restaurar sesiones de música previas
        self.loop.create_task(music_service.restore_players(self))

async def main():
    bot = BotPersonal()
    async with bot:
        try:
            await bot.start(settings.TOKEN)
        finally:
            logger.info("--- 🛑 APAGANDO SERVICIOS ---")
            await db_service.close_db()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # El logger ya registrará el cierre en finally