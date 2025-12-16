import discord
import datetime
from discord.ext import commands
from services import random_service, embed_service, db_service, lang_service

class Chaos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Memoria RAM: {guild_id: {'enabled': bool, 'prob': float}}
        self.cache = {}

    async def get_config(self, guild_id: int):
        """
        Obtiene la config desde la memoria RAM.
        Si no existe, la busca en la DB y la guarda en RAM.
        """
        if guild_id not in self.cache:
            row = await db_service.fetch_one("SELECT chaos_enabled, chaos_probability FROM guild_config WHERE guild_id = ?", (guild_id,))
            if row:
                self.cache[guild_id] = {
                    'enabled': bool(row['chaos_enabled']),
                    'prob': float(row['chaos_probability'])
                }
            else:
                # Valores por defecto si no está configurado
                self.cache[guild_id] = {'enabled': True, 'prob': 0.01}
        
        return self.cache[guild_id]

    def update_local_config(self, guild_id: int, enabled: bool, prob: float):
        """Método público para actualizar la caché instantáneamente desde otro comando."""
        self.cache[guild_id] = {'enabled': enabled, 'prob': prob}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return

        # 1. Leemos de RAM (¡Ultra rápido!)
        config = await self.get_config(message.guild.id)
        
        if not config['enabled']: return

        # 2. Verificamos suerte
        if random_service.verificar_suerte(config['prob']):
            try:
                lang = await lang_service.get_guild_lang(message.guild.id)
                
                # Timeout del usuario
                await message.author.timeout(datetime.timedelta(minutes=1), reason="Chaos Roulette")
                
                # Mensaje visual
                txt = lang_service.get_text("chaos_bang", lang, user=message.author.name, prob=int(config['prob']*100))
                await message.channel.send(embed=embed_service.info("🔫 Bang!", txt))
            except discord.Forbidden:
                # Si el bot no tiene permisos, simplemente lo ignora para no spamear errores
                pass
            except Exception as e:
                print(f"Error en Chaos: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Chaos(bot))