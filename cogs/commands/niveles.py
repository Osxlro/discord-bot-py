import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
from services import db_service, embed_service

class Niveles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1, 60.0, commands.BucketType.user) # 1 mensaje cada 60s da XP

    def get_ratelimit(self, message: discord.Message):
        """Evita el spam de XP."""
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # 1. Verificar Cooldown (Para que no ganen XP por spamear "hola" 20 veces)
        if self.get_ratelimit(message):
            return

        # 2. Calcular XP ganada (Random entre 15 y 25)
        xp_ganada = random.randint(15, 25)

        # 3. Obtener datos actuales
        row = await db_service.fetch_one("SELECT xp, level FROM users WHERE user_id = ?", (message.author.id,))
        
        if not row:
            # Usuario nuevo
            xp_actual = 0
            nivel_actual = 1
            await db_service.execute("INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)", (message.author.id, xp_ganada, 1))
        else:
            xp_actual = row['xp']
            nivel_actual = row['level']
            
            # Actualizar XP
            nuevo_total_xp = xp_actual + xp_ganada
            
            # 4. Verificar Subida de Nivel
            # Fórmula: Nivel * 100 (Ej: Para pasar a nivel 2 necesitas 100xp acumulada total)
            xp_necesaria_siguiente = nivel_actual * 100 
            
            if nuevo_total_xp >= xp_necesaria_siguiente:
                nivel_actual += 1
                await message.channel.send(f"🎉 ¡Felicidades {message.author.mention}! Has subido al **Nivel {nivel_actual}** 🆙")
            
            # Guardar en DB
            await db_service.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (nuevo_total_xp, nivel_actual, message.author.id))

    @commands.hybrid_command(name="rank", description="Muestra tu nivel y experiencia actual")
    async def rank(self, ctx: commands.Context, usuario: discord.Member = None):
        target = usuario or ctx.author
        
        row = await db_service.fetch_one("SELECT xp, level FROM users WHERE user_id = ?", (target.id,))
        
        if not row:
            embed = embed_service.info("Sin Rango", f"{target.name} aún no tiene experiencia registrada.")
            await ctx.reply(embed=embed)
            return

        xp = row['xp']
        nivel = row['level']
        xp_next = nivel * 100 # Meta para el siguiente nivel
        
        # Barra de progreso visual
        porcentaje = min(xp / xp_next, 1.0)
        bloques = int(porcentaje * 10)
        barra = "🟩" * bloques + "⬜" * (10 - bloques)

        embed = embed_service.info(f"Rango de {target.name}", "")
        embed.add_field(name="Nivel", value=f"🏆 **{nivel}**", inline=True)
        embed.add_field(name="XP Total", value=f"✨ `{xp} / {xp_next}`", inline=True)
        embed.add_field(name="Progreso", value=f"{barra} {int(porcentaje*100)}%", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.reply(embed=embed)

    # --- MENÚ CONTEXTUAL: Ver Rank (Click Derecho) ---
    # Esto demuestra tu duda anterior: El menú vive junto al comando, no en un servicio aparte.
    @app_commands.context_menu(name="Ver Rank")
    async def ver_rank_menu(self, interaction: discord.Interaction, member: discord.Member):
        # Reutilizamos la lógica llamando al comando (o duplicamos la consulta si prefieres pureza)
        # Aquí haremos la consulta directa para ser rápidos
        row = await db_service.fetch_one("SELECT xp, level FROM users WHERE user_id = ?", (member.id,))
        
        if not row:
            await interaction.response.send_message(f"{member.name} no tiene rango.", ephemeral=True)
            return

        xp = row['xp']
        nivel = row['level']
        
        embed = embed_service.info(f"Rango de {member.name}", f"🏆 Nivel: **{nivel}**\n✨ XP: `{xp}`")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Niveles(bot))