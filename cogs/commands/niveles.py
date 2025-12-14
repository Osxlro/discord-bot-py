import discord
from discord.ext import commands
from discord import app_commands
import random
from services import db_service, embed_service

class Niveles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1, 60.0, commands.BucketType.user)

        self.ctx_menu = app_commands.ContextMenu(
            name="Ver Rank",
            callback=self.ver_rank_menu
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    def get_ratelimit(self, message: discord.Message):
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        if self.get_ratelimit(message): return

        xp_ganada = random.randint(15, 25)
        
        # Obtenemos datos del usuario Y config del servidor al mismo tiempo si es posible, 
        # pero por orden haremos dos consultas rápidas.
        row = await db_service.fetch_one("SELECT xp, level FROM users WHERE user_id = ?", (message.author.id,))
        
        if not row:
            nivel_actual = 1
            await db_service.execute("INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)", (message.author.id, xp_ganada, 1))
        else:
            xp_actual = row['xp']
            nivel_actual = row['level']
            nuevo_total_xp = xp_actual + xp_ganada
            xp_necesaria = nivel_actual * 100 
            
            if nuevo_total_xp >= xp_necesaria:
                nivel_actual += 1
                
                # BUSCAR MENSAJE PERSONALIZADO
                guild_conf = await db_service.fetch_one("SELECT level_msg FROM guild_config WHERE guild_id = ?", (message.guild.id,))
                
                msg_raw = guild_conf['level_msg'] if guild_conf and guild_conf['level_msg'] else "🎉 ¡Felicidades {user}! Has subido al **Nivel {level}** 🆙"
                
                # Reemplazar variables
                msg_final = msg_raw.replace("{user}", message.author.mention).replace("{level}", str(nivel_actual))
                
                await message.channel.send(msg_final)
            
            await db_service.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (nuevo_total_xp, nivel_actual, message.author.id))

    # --- COMANDO PRINCIPAL CON SUBCOMANDOS ---
    @commands.hybrid_group(name="rank", description="Sistema de Niveles")
    async def rank_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            # Si usa solo /rank, mostramos su status
            await self.ver_status(ctx, ctx.author)

    @rank_group.command(name="user", description="Ver el rango de un usuario")
    async def user_rank(self, ctx: commands.Context, usuario: discord.Member):
        await self.ver_status(ctx, usuario)

    @rank_group.command(name="leaderboard", description="Ver el top 10 de usuarios con más XP")
    async def leaderboard(self, ctx: commands.Context):
        # Nota: Esto es global (todos los usuarios de la DB). 
        # Si quieres solo del servidor, habría que filtrar en Python o tener una tabla por servidor.
        # Por simplicidad en SQLite simple, lo haremos global del bot.
        rows = await db_service.fetch_all("SELECT user_id, level, xp FROM users ORDER BY xp DESC LIMIT 10")
        
        if not rows:
            await ctx.reply(embed=embed_service.info("Vacío", "Nadie tiene experiencia aún."))
            return

        desc = ""
        for i, row in enumerate(rows, 1):
            user_id = row['user_id']
            # Intentar obtener nombre (puede que no esté en este server)
            user = self.bot.get_user(user_id)
            name = user.name if user else f"Usuario ID {user_id}"
            
            medalla = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            desc += f"**{medalla} {name}** • Nvl {row['level']} ({row['xp']} XP)\n"

        embed = embed_service.info("🏆 Tabla de Clasificación", desc)
        await ctx.reply(embed=embed)

    # Función auxiliar para ver status (reutilizada)
    async def ver_status(self, ctx, target):
        row = await db_service.fetch_one("SELECT xp, level FROM users WHERE user_id = ?", (target.id,))
        if not row:
            await ctx.reply(embed=embed_service.info("Sin Rango", f"{target.name} no tiene XP."), ephemeral=True)
            return

        xp, nivel = row['xp'], row['level']
        xp_next = nivel * 100
        porcentaje = min(xp / xp_next, 1.0) if xp_next > 0 else 0
        bloques = int(porcentaje * 10)
        barra = "🟩" * bloques + "⬜" * (10 - bloques)

        embed = embed_service.info(f"Rango de {target.name}", "")
        embed.add_field(name="Nivel", value=f"🏆 **{nivel}**", inline=True)
        embed.add_field(name="XP", value=f"✨ `{xp} / {xp_next}`", inline=True)
        embed.add_field(name="Progreso", value=f"{barra} {int(porcentaje*100)}%", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.reply(embed=embed)

    # Callback Menú
    async def ver_rank_menu(self, interaction: discord.Interaction, member: discord.Member):
        row = await db_service.fetch_one("SELECT xp, level FROM users WHERE user_id = ?", (member.id,))
        if not row:
            await interaction.response.send_message("Sin datos de XP.", ephemeral=True)
            return
        embed = embed_service.info(f"Rango de {member.name}", f"🏆 Nivel: **{row['level']}**\n✨ XP: `{row['xp']}`")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Niveles(bot))