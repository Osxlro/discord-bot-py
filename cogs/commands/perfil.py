import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal, Optional
from services import db_service, embed_service

class Perfil(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="perfil", description="Muestra tu tarjeta de usuario o la de otro")
    async def perfil(self, ctx: commands.Context, usuario: discord.Member = None):
        target = usuario or ctx.author
        
        # 1. Obtener Datos Globales
        user_data = await db_service.fetch_one("SELECT * FROM users WHERE user_id = ?", (target.id,))
        
        # 2. Obtener Datos del Servidor
        guild_data = await db_service.fetch_one(
            "SELECT xp, level FROM guild_stats WHERE guild_id = ? AND user_id = ?", 
            (ctx.guild.id, target.id)
        )

        desc = user_data['description'] if user_data else "Sin descripción."
        cumple = user_data['birthday'] if user_data and user_data['birthday'] else "No establecido"
        prefix = user_data['custom_prefix'] if user_data and user_data['custom_prefix'] else "!"
        
        xp = guild_data['xp'] if guild_data else 0
        nivel = guild_data['level'] if guild_data else 1
        
        xp_next = nivel * 100
        progreso = min(xp / xp_next, 1.0)
        bloques = int(progreso * 10)
        barra = "▰" * bloques + "▱" * (10 - bloques)

        embed = discord.Embed(title=f"Tarjeta de {target.display_name}", color=target.color)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="📝 Descripción", value=f"*{desc}*", inline=False)
        embed.add_field(name="🎂 Cumpleaños", value=f"📅 {cumple}", inline=True)
        embed.add_field(name="⌨️ Prefix", value=f"`{prefix}`", inline=True)
        
        embed.add_field(name="⠀", value="**--- Estadísticas del Servidor ---**", inline=False)
        embed.add_field(name="🏆 Nivel", value=f"**{nivel}**", inline=True)
        embed.add_field(name="✨ XP Total", value=f"{xp}", inline=True)
        embed.add_field(name=f"Progreso ({int(progreso*100)}%)", value=f"`{barra}` {xp}/{xp_next}", inline=False)

        # --- SECCIÓN DE MENSAJES PERSONALIZADOS ---
        msgs_texto = ""
        if user_data:
            if user_data['personal_level_msg']:
                msgs_texto += f"**• Nivel:** \"{user_data['personal_level_msg'][:40]}...\"\n"
            if user_data['personal_birthday_msg']:
                msgs_texto += f"**• Cumple:** \"{user_data['personal_birthday_msg'][:40]}...\"\n"
        
        if msgs_texto:
            embed.add_field(name="--- Mensajes Personalizados ---", value=msgs_texto, inline=False)

        await ctx.reply(embed=embed)

    # --- COMANDOS DE PERSONALIZACIÓN ---
    
    @commands.hybrid_group(name="mi_perfil", description="Personaliza tu tarjeta y mensajes")
    async def mi_perfil(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @mi_perfil.command(name="descripcion", description="Cambia la descripción de tu tarjeta")
    async def set_desc(self, ctx: commands.Context, texto: str):
        if len(texto) > 200:
            await ctx.reply("La descripción es muy larga (máx 200 caracteres).", ephemeral=True)
            return
            
        check = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        if not check:
            await db_service.execute("INSERT INTO users (user_id, description) VALUES (?, ?)", (ctx.author.id, texto))
        else:
            await db_service.execute("UPDATE users SET description = ? WHERE user_id = ?", (texto, ctx.author.id))
            
        await ctx.reply(embed=embed_service.success("Perfil Actualizado", "Tu descripción ha sido guardada."))

    @mi_perfil.command(name="mensaje_nivel", description="Define tu propio mensaje cuando subas de nivel")
    @app_commands.describe(mensaje="Usa {user}, {level}, {server}. Escribe 'reset' para usar el del servidor.")
    async def set_level_msg(self, ctx: commands.Context, mensaje: str):
        val = None if mensaje.lower() == "reset" else mensaje
        
        check = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        if not check:
            await db_service.execute("INSERT INTO users (user_id, personal_level_msg) VALUES (?, ?)", (ctx.author.id, val))
        else:
            await db_service.execute("UPDATE users SET personal_level_msg = ? WHERE user_id = ?", (val, ctx.author.id))
            
        await ctx.reply(embed=embed_service.success("Mensaje Personal", "Tu mensaje de nivel ha sido configurado."))

    @mi_perfil.command(name="mensaje_cumple", description="Define tu propio mensaje de cumpleaños")
    @app_commands.describe(mensaje="Usa {user}. Escribe 'reset' para usar el del servidor.")
    async def set_bday_msg(self, ctx: commands.Context, mensaje: str):
        val = None if mensaje.lower() == "reset" else mensaje
        
        check = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        if not check:
            await db_service.execute("INSERT INTO users (user_id, personal_birthday_msg) VALUES (?, ?)", (ctx.author.id, val))
        else:
            await db_service.execute("UPDATE users SET personal_birthday_msg = ? WHERE user_id = ?", (val, ctx.author.id))
            
        await ctx.reply(embed=embed_service.success("Mensaje Personal", "Tu mensaje de cumpleaños ha sido configurado."))

async def setup(bot: commands.Bot):
    await bot.add_cog(Perfil(bot))