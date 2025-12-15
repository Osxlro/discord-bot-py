import discord
from discord.ext import commands
import random
from services import db_service, embed_service, lang_service

class Niveles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1, 60.0, commands.BucketType.user)

    def get_ratelimit(self, message: discord.Message):
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        if self.get_ratelimit(message): return

        xp_ganada = random.randint(15, 25)
        row = await db_service.fetch_one("SELECT xp, level FROM guild_stats WHERE guild_id = ? AND user_id = ?", (message.guild.id, message.author.id))
        
        if not row:
            nivel_actual = 1
            await db_service.execute("INSERT INTO guild_stats (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?)", (message.guild.id, message.author.id, xp_ganada, 1))
        else:
            xp_actual = row['xp']
            nivel_actual = row['level']
            nuevo_total_xp = xp_actual + xp_ganada
            xp_necesaria = nivel_actual * 100 
            
            if nuevo_total_xp >= xp_necesaria:
                nivel_actual += 1
                
                # Obtener idioma
                lang = await lang_service.get_guild_lang(message.guild.id)
                
                # Mensaje de nivel
                user_conf = await db_service.fetch_one("SELECT personal_level_msg FROM users WHERE user_id = ?", (message.author.id,))
                guild_conf = await db_service.fetch_one("SELECT server_level_msg FROM guild_config WHERE guild_id = ?", (message.guild.id,))
                
                if user_conf and user_conf['personal_level_msg']:
                    msg_raw = user_conf['personal_level_msg']
                elif guild_conf and guild_conf['server_level_msg']:
                    msg_raw = guild_conf['server_level_msg']
                else:
                    msg_raw = lang_service.get_text("level_up_default", lang)
                
                msg_final = msg_raw.replace("{user}", message.author.mention).replace("{level}", str(nivel_actual)).replace("{server}", message.guild.name)
                await message.channel.send(msg_final)
            
            await db_service.execute("UPDATE guild_stats SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?", (nuevo_total_xp, nivel_actual, message.guild.id, message.author.id))

    @commands.hybrid_command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        rows = await db_service.fetch_all("SELECT user_id, level, xp FROM guild_stats WHERE guild_id = ? ORDER BY xp DESC LIMIT 10", (ctx.guild.id,))
        
        if not rows:
            msg = lang_service.get_text("leaderboard_empty", lang)
            await ctx.reply(embed=embed_service.info("Vacío", msg))
            return

        desc = ""
        for i, row in enumerate(rows, 1):
            user_id = row['user_id']
            user = ctx.guild.get_member(user_id)
            name = user.display_name if user else f"User {user_id}"
            medalla = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            desc += f"**{medalla} {name}** • Lvl {row['level']} ({row['xp']} XP)\n"

        title = lang_service.get_text("leaderboard_title", lang, server=ctx.guild.name)
        await ctx.reply(embed=embed_service.info(title, desc))

async def setup(bot: commands.Bot):
    await bot.add_cog(Niveles(bot))