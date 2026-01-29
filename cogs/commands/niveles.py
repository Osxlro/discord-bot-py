import discord
from discord.ext import commands
from config import locales
import random
from services import db_service, embed_service, lang_service

class Niveles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cooldown: 1 mensaje cada 60 segundos por usuario da XP
        self._cd = commands.CooldownMapping.from_cooldown(1, 60.0, commands.BucketType.user)

    def get_ratelimit(self, message: discord.Message):
        """Retorna True si el usuario está en cooldown (ya ganó XP recientemente)."""
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        # Si está en cooldown (escribiendo muy rápido), ignoramos para no saturar la DB
        if self.get_ratelimit(message): return

        # Fórmula simple de XP (15 a 25 puntos por mensaje)
        xp_ganada = random.randint(15, 25)
        
        # 1. Consultamos XP actual (Lectura rápida gracias al Singleton)
        row = await db_service.fetch_one(
            "SELECT xp, level FROM guild_stats WHERE guild_id = ? AND user_id = ?", 
            (message.guild.id, message.author.id)
        )
        
        if not row:
            # Primera vez que habla
            await db_service.execute(
                "INSERT INTO guild_stats (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?)", 
                (message.guild.id, message.author.id, xp_ganada, 1)
            )
        else:
            xp_actual = row['xp']
            nivel_actual = row['level']
            nuevo_total_xp = xp_actual + xp_ganada
            
            # Fórmula RPG: Nivel * 100 (Nvl 1->100, Nvl 2->200...)
            xp_necesaria = nivel_actual * 100 
            
            if nuevo_total_xp >= xp_necesaria:
                nivel_actual += 1
                await self._enviar_mensaje_nivel(message, nivel_actual)
            
            # Guardamos progreso
            await db_service.execute(
                "UPDATE guild_stats SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?", 
                (nuevo_total_xp, nivel_actual, message.guild.id, message.author.id)
            )

    async def _enviar_mensaje_nivel(self, message: discord.Message, nuevo_nivel: int):
        """Maneja el envío del mensaje de felicitación."""
        try:
            lang = await lang_service.get_guild_lang(message.guild.id)
            
            # Buscamos configuraciones personalizadas
            user_conf = await db_service.fetch_one("SELECT personal_level_msg FROM users WHERE user_id = ?", (message.author.id,))
            guild_conf = await db_service.fetch_one("SELECT server_level_msg FROM guild_config WHERE guild_id = ?", (message.guild.id,))
            
            # Prioridad: Usuario > Servidor > Default
            if user_conf and user_conf['personal_level_msg']:
                msg_raw = user_conf['personal_level_msg']
            elif guild_conf and guild_conf['server_level_msg']:
                msg_raw = guild_conf['server_level_msg']
            else:
                msg_raw = lang_service.get_text("level_up_default", lang)
            
            msg_final = msg_raw.replace("{user}", message.author.mention)\
                               .replace("{level}", str(nuevo_nivel))\
                               .replace("{server}", message.guild.name)
            
            await message.channel.send(msg_final)
        except Exception as e:
            print(f"Error enviando nivel: {e}")

    @commands.hybrid_command(name="leaderboard", description="Muestra el top de XP del servidor")
    async def leaderboard(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Obtenemos el TOP 10
        rows = await db_service.fetch_all(
            "SELECT user_id, level, xp FROM guild_stats WHERE guild_id = ? ORDER BY xp DESC LIMIT 10", 
            (ctx.guild.id,)
        )
        
        if not rows:
            msg = lang_service.get_text("leaderboard_empty", lang)
            await ctx.reply(embed=embed_service.info("Vacío", msg))
            return

        desc = ""
        for i, row in enumerate(rows, 1):
            user_id = row['user_id']
            # Intentamos obtener el usuario del caché del bot, si no, mostramos ID
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"Usuario {user_id}"
            
            medalla = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            desc += f"**{medalla} {name}** • Nvl {row['level']} \n"

        title = lang_service.get_text("leaderboard_title", lang, server=ctx.guild.name)
        await ctx.reply(embed=embed_service.info(title, desc, thumbnail=ctx.guild.icon.url if ctx.guild.icon else None))

    class Niveles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rebirth", description="Reinicia tu nivel (requiere Nivel 100) para ganar un Rebirth.")
    async def rebirth(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        success, result = await db_service.do_rebirth(interaction.guild.id, interaction.user.id)
        
        if success:
            msg = locales.ES['rebirth_success'].format(rebirths=result)
            # Podríamos añadir un rol especial aquí si quisieras
        else:
            if isinstance(result, int):
                msg = locales.ES['rebirth_fail_level'].format(level=result)
            else:
                msg = locales.ES['rebirth_fail_generic']
        
        await interaction.followup.send(msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(Niveles(bot))