import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import db_service, embed_service, lang_service
from config import settings

class Perfil(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="perfil", description="Gestión de perfil de usuario.", fallback="ver")
    @app_commands.describe(usuario="El usuario del que quieres ver el perfil (vacío para ver el tuyo)")
    async def perfil(self, ctx: commands.Context, usuario: discord.Member = None):
        target = usuario or ctx.author
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Recuperamos datos
        user_data = await db_service.fetch_one("SELECT * FROM users WHERE user_id = ?", (target.id,))
        guild_data = await db_service.fetch_one("SELECT xp, level, rebirths FROM guild_stats WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, target.id))

        # Datos de usuario
        desc = user_data['description'] if user_data else lang_service.get_text("profile_desc", lang)
        cumple = user_data['birthday'] if user_data and user_data['birthday'] else lang_service.get_text("profile_no_bday", lang)
        prefix = user_data['custom_prefix'] if user_data and user_data['custom_prefix'] else "!"
        
        # Datos del servidor
        xp = guild_data['xp'] if guild_data else 0
        nivel = guild_data['level'] if guild_data else 1
        rebirths = guild_data['rebirths'] if guild_data else 0
        
        # Barra de progreso
        xp_next = db_service.calculate_xp_required(nivel)
        progreso = min(xp / xp_next, 1.0)
        bloques = int(progreso * 10)
        barra = settings.UI_CONFIG["PROGRESS_BAR_FILLED"] * bloques + settings.UI_CONFIG["PROGRESS_BAR_EMPTY"] * (10 - bloques)

        # Embed
        title = lang_service.get_text("profile_title", lang, user=target.display_name)
        embed = discord.Embed(title=title, color=target.color)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name=lang_service.get_text("profile_field_desc", lang), value=f"*{desc}*", inline=False)
        embed.add_field(name=lang_service.get_text("profile_field_bday", lang), value=f"📅 {cumple}", inline=True)
        embed.add_field(name=lang_service.get_text("profile_field_prefix", lang), value=f"`{prefix}`", inline=True)
        
        stats_title = lang_service.get_text("profile_server_stats", lang)
        embed.add_field(name="⠀", value=stats_title, inline=False)
        
        embed.add_field(name=lang_service.get_text("profile_field_lvl", lang), value=f"**{nivel}**", inline=True)
        embed.add_field(name=lang_service.get_text("profile_field_rebirths", lang), value=f"**{rebirths}**", inline=True)
        embed.add_field(name=lang_service.get_text("profile_field_xp", lang), value=f"{xp}", inline=True)
        
        embed.add_field(name=f"Progress ({int(progreso*100)}%)", value=f"`{barra}` {xp}/{xp_next}", inline=False)

        msgs = ""
        if user_data:
            if user_data['personal_level_msg']: msgs += f"**• Lvl Msg:** \"{user_data['personal_level_msg'][:30]}...\"\n"
            if user_data['personal_birthday_msg']: msgs += f"**• Bday Msg:** \"{user_data['personal_birthday_msg'][:30]}...\"\n"
        
        if msgs:
            embed.add_field(name=lang_service.get_text("profile_custom_msgs", lang), value=msgs, inline=False)

        await ctx.reply(embed=embed)

    @perfil.command(name="descripcion", description="Cambia la biografía de tu tarjeta.")
    @app_commands.describe(texto="Máximo 200 caracteres.")
    async def set_desc(self, ctx: commands.Context, texto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        if len(texto) > settings.UI_CONFIG["MAX_DESC_LENGTH"]: 
            await ctx.reply(lang_service.get_text("error_max_chars", lang, max=settings.UI_CONFIG["MAX_DESC_LENGTH"]), ephemeral=True)
            return
        
        # Optimización: INSERT OR REPLACE para evitar doble consulta
        await db_service.execute("""
            INSERT INTO users (user_id, description) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET description = excluded.description
        """, (ctx.author.id, texto))
        
        await ctx.reply(embed=embed_service.success(lang_service.get_text("profile_update_success", lang), lang_service.get_text("profile_desc_saved", lang), lite=True))

    @perfil.command(name="mensaje", description="Personaliza tus mensajes de nivel o cumpleaños.")
    @app_commands.describe(
        tipo="¿Qué mensaje quieres personalizar?",
        texto="Tu mensaje. Usa {user}, {level} (solo nivel). Escribe 'reset' para borrar."
    )
    async def set_personal_msg(self, ctx: commands.Context, tipo: Literal["Nivel", "Cumpleaños"], texto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = None if texto.lower() == "reset" else texto
        columna = "personal_level_msg" if tipo == "Nivel" else "personal_birthday_msg"
        
        # Optimización: INSERT OR REPLACE
        await db_service.execute(f"""
            INSERT INTO users (user_id, {columna}) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET {columna} = excluded.{columna}
        """, (ctx.author.id, val))
        
        await ctx.reply(embed=embed_service.success(lang_service.get_text("profile_update_success", lang), lang_service.get_text("profile_msg_saved", lang), lite=True))

async def setup(bot: commands.Bot):
    await bot.add_cog(Perfil(bot))