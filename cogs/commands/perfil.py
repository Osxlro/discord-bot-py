import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import db_service, embed_service, lang_service

class Perfil(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="perfil", description="Muestra tu tarjeta de perfil o la de otro usuario.")
    @app_commands.describe(usuario="El usuario del que quieres ver el perfil (vacío para ver el tuyo)")
    async def perfil(self, ctx: commands.Context, usuario: discord.Member = None):
        target = usuario or ctx.author
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # 1. Recuperamos datos
        user_data = await db_service.fetch_one("SELECT * FROM users WHERE user_id = ?", (target.id,))
        guild_data = await db_service.fetch_one("SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, target.id))

        # Datos de usuario (Globales)
        desc = user_data['description'] if user_data else lang_service.get_text("profile_desc", lang)
        cumple = user_data['birthday'] if user_data and user_data['birthday'] else lang_service.get_text("profile_no_bday", lang)
        prefix = user_data['custom_prefix'] if user_data and user_data['custom_prefix'] else "!"
        
        # Datos del servidor (Locales)
        xp = guild_data['xp'] if guild_data else 0
        nivel = guild_data['level'] if guild_data else 1
        rebirths = guild_data['rebirths'] if guild_data else 0 # <--- NUEVO VARIABLE
        
        # Cálculo de barra de progreso (Sincronizado con db_service)
        xp_next = int(100 * (nivel ** 1.2)) 
        progreso = min(xp / xp_next, 1.0)
        bloques = int(progreso * 10)
        barra = "▰" * bloques + "▱" * (10 - bloques)

        # Construcción del Embed
        title = lang_service.get_text("profile_title", lang, user=target.display_name)
        embed = discord.Embed(title=title, color=target.color)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="📝 Desc", value=f"*{desc}*", inline=False)
        embed.add_field(name="🎂 Birth Date", value=f"📅 {cumple}", inline=True)
        embed.add_field(name="⌨️ Prefix", value=f"`{prefix}`", inline=True)
        
        stats_title = lang_service.get_text("profile_server_stats", lang)
        embed.add_field(name="⠀", value=stats_title, inline=False)
        
        # --- FILA DE ESTADÍSTICAS (CON REBIRTHS) ---
        embed.add_field(name="🏆 Lvl", value=f"**{nivel}**", inline=True)
        embed.add_field(name="🌀 Rebirths", value=f"**{rebirths}**", inline=True) # <--- CAMPO NUEVO
        embed.add_field(name="✨ XP", value=f"{xp}", inline=True)
        
        embed.add_field(name=f"Progress ({int(progreso*100)}%)", value=f"`{barra}` {xp}/{xp_next}", inline=False)

        # Mensajes personalizados
        msgs = ""
        if user_data:
            if user_data['personal_level_msg']: msgs += f"**• Lvl Msg:** \"{user_data['personal_level_msg'][:30]}...\"\n"
            if user_data['personal_birthday_msg']: msgs += f"**• Bday Msg:** \"{user_data['personal_birthday_msg'][:30]}...\"\n"
        
        if msgs:
            embed.add_field(name=lang_service.get_text("profile_custom_msgs", lang), value=msgs, inline=False)

        await ctx.reply(embed=embed)

    @commands.hybrid_group(name="mi_perfil", description="Comandos para editar tu perfil personal.")
    async def mi_perfil(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None: await ctx.send_help(ctx.command)

    @mi_perfil.command(name="descripcion", description="Establece la biografía de tu tarjeta de perfil.")
    @app_commands.describe(texto="Máximo 200 caracteres.")
    async def set_desc(self, ctx: commands.Context, texto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if len(texto) > 200: 
            await ctx.reply("Max 200 chars.", ephemeral=True)
            return
        
        check = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        if not check: await db_service.execute("INSERT INTO users (user_id, description) VALUES (?, ?)", (ctx.author.id, texto))
        else: await db_service.execute("UPDATE users SET description = ? WHERE user_id = ?", (texto, ctx.author.id))
        
        await ctx.reply(embed=embed_service.success(lang_service.get_text("profile_update_success", lang), lang_service.get_text("profile_desc_saved", lang), lite=True))

    @mi_perfil.command(name="mensaje", description="Personaliza tus mensajes automáticos.")
    @app_commands.describe(
        tipo="¿Qué mensaje quieres personalizar?",
        texto="Tu mensaje. Usa {user}, {level} (solo nivel). Escribe 'reset' para borrar."
    )
    async def set_personal_msg(self, ctx: commands.Context, tipo: Literal["Nivel", "Cumpleaños"], texto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = None if texto.lower() == "reset" else texto
        columna = "personal_level_msg" if tipo == "Nivel" else "personal_birthday_msg"
        
        check = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        if not check: 
            await db_service.execute(f"INSERT INTO users (user_id, {columna}) VALUES (?, ?)", (ctx.author.id, val))
        else: 
            await db_service.execute(f"UPDATE users SET {columna} = ? WHERE user_id = ?", (val, ctx.author.id))
        
        await ctx.reply(embed=embed_service.success("Perfil Actualizado", f"✅ Mensaje de **{tipo}** guardado.", lite=True))

async def setup(bot: commands.Bot):
    await bot.add_cog(Perfil(bot))