import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal, Optional
from services import db_service, embed_service

class Configuracion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="config", description="Panel de configuración del Bot")
    async def config(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    # --- 1. CONFIGURACIÓN DE USUARIO (Cualquiera puede usarlo) ---
    @config.command(name="prefix", description="Cambia tu prefijo personal")
    async def set_prefix(self, ctx: commands.Context, nuevo: str):
        if len(nuevo) > 5:
            await ctx.reply("El prefijo no puede tener más de 5 caracteres.", ephemeral=True)
            return

        check = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        if not check:
            await db_service.execute("INSERT INTO users (user_id, custom_prefix) VALUES (?, ?)", (ctx.author.id, nuevo))
        else:
            await db_service.execute("UPDATE users SET custom_prefix = ? WHERE user_id = ?", (nuevo, ctx.author.id))
            
        embed = embed_service.success("Prefijo Personal", f"Ahora puedes usarme con: `{nuevo}` (ej: `{nuevo}ping`)")
        await ctx.reply(embed=embed)

    # --- 2. CONFIGURACIÓN DE SERVIDOR (Unificado) ---
    @config.command(name="server", description="Configura canales y opciones del servidor")
    @app_commands.describe(
        ajuste="¿Qué sistema quieres configurar?",
        canal="[Opcional] Selecciona el canal (solo para Bienvenidas, Logs, Confesiones)",
        texto="[Opcional] Escribe el mensaje (solo para Mención). Usa 'reset' para borrar."
    )
    @commands.has_permissions(administrator=True)
    async def server_config(
        self, 
        ctx: commands.Context, 
        ajuste: Literal["Bienvenidas", "Logs", "Confesiones", "Mencion", "Cumpleaños"],
        canal: Optional[discord.TextChannel] = None,
        texto: Optional[str] = None
    ):
        guild_id = ctx.guild.id

        # CASO A: Configuración de Texto (Mención)
        if ajuste == "Mencion":
            if not texto:
                await ctx.reply(embed=embed_service.error("Faltan datos", "Para configurar la mención, debes escribir algo en el campo `texto`."), ephemeral=True)
                return
            
            valor = None if texto.lower() == "reset" else texto
            msg_exito = "Mensaje restablecido." if not valor else f"✅ Respuesta actualizada a: **{texto}**"
            
            await db_service.execute("""
                INSERT INTO guild_config (guild_id, mention_response) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET mention_response = excluded.mention_response
            """, (guild_id, valor))
            
            await ctx.reply(embed=embed_service.success("Configuración Actualizada", msg_exito))

        # CASO B: Configuración de Canales
        else:
            if not canal:
                await ctx.reply(embed=embed_service.error("Faltan datos", f"Para configurar **{ajuste}**, debes seleccionar un canal en el campo `canal`."), ephemeral=True)
                return

            # Mapeo de la opción elegida -> columna en base de datos
            col_map = {
                "Bienvenidas": "welcome_channel_id",
                "Logs": "logs_channel_id",
                "Confesiones": "confessions_channel_id",
                "Cumpleaños": "birthday_channel_id"
            }
            columna = col_map[ajuste]
            
            # Query dinámica segura
            query = f"""
                INSERT INTO guild_config (guild_id, {columna}) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET {columna} = excluded.{columna}
            """
            await db_service.execute(query, (guild_id, canal.id))
            
            await ctx.reply(embed=embed_service.success(f"{ajuste}", f"✅ Configurado en: {canal.mention}"))

async def setup(bot: commands.Bot):
    await bot.add_cog(Configuracion(bot))