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

    # --- 2. CONFIGURACIÓN DE SERVIDOR ---
    @config.command(name="server", description="Configura canales y opciones del servidor")
    @app_commands.describe(
        ajuste="¿Qué sistema quieres configurar?",
        canal="[Opcional] Selecciona el canal (para Bienvenidas, Logs, Confesiones)",
        texto="[Opcional] Escribe el texto (para Mención o Nivel). Usa 'reset' para borrar.",
        rol="[Opcional] Selecciona el rol (para Auto Rol)"
    )
    @commands.has_permissions(administrator=True)
    async def server_config(
        self, 
        ctx: commands.Context, 
        ajuste: Literal["Bienvenidas", "Logs", "Confesiones", "Mencion", "Cumpleaños", "Auto Rol", "Mensaje Nivel"],
        canal: Optional[discord.TextChannel] = None,
        texto: Optional[str] = None,
        rol: Optional[discord.Role] = None
    ):
        guild_id = ctx.guild.id

        # CASO: Auto Rol
        if ajuste == "Auto Rol":
            if not rol:
                # Si escribe 'reset' en texto y no pone rol, borramos la config
                if texto and texto.lower() == "reset":
                    await db_service.execute("UPDATE guild_config SET autorole_id = 0 WHERE guild_id = ?", (guild_id,))
                    await ctx.reply(embed=embed_service.success("Auto Rol Desactivado", "Ya no se entregarán roles al entrar."))
                    return

                await ctx.reply(embed=embed_service.error("Faltan datos", "Debes seleccionar un `rol`."), ephemeral=True)
                return
            
            # Validación de jerarquía (Bug Fix)
            if rol.position >= ctx.guild.me.top_role.position:
                await ctx.reply(embed=embed_service.error("Error", "Ese rol es superior a los míos."), ephemeral=True)
                return

            await db_service.execute("""
                INSERT INTO guild_config (guild_id, autorole_id) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET autorole_id = excluded.autorole_id
            """, (guild_id, rol.id))
            
            await ctx.reply(embed=embed_service.success("Auto Rol", f"✅ Nuevo rol de entrada: {rol.mention}"))

        # CASO: Mensajes de Texto (Mención y Nivel)
        elif ajuste in ["Mencion", "Mensaje Nivel"]:
            if not texto:
                ejemplo = "¡Felicidades {user}, eres nivel {level}!" if ajuste == "Mensaje Nivel" else "Hola..."
                await ctx.reply(embed=embed_service.error("Faltan datos", f"Debes escribir el mensaje en `texto`.\nEjemplo: `{ejemplo}`"), ephemeral=True)
                return
            
            columna = "mention_response" if ajuste == "Mencion" else "level_msg"
            valor = None if texto.lower() == "reset" else texto
            
            query = f"INSERT INTO guild_config (guild_id, {columna}) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET {columna} = excluded.{columna}"
            await db_service.execute(query, (guild_id, valor))
            
            await ctx.reply(embed=embed_service.success(f"{ajuste}", "✅ Configuración de texto actualizada."))

        # CASO: Canales
        else:
            if not canal:
                await ctx.reply(embed=embed_service.error("Faltan datos", f"Para configurar **{ajuste}**, selecciona un `canal`."), ephemeral=True)
                return

            col_map = {
                "Bienvenidas": "welcome_channel_id",
                "Logs": "logs_channel_id",
                "Confesiones": "confessions_channel_id",
                "Cumpleaños": "birthday_channel_id"
            }
            columna = col_map[ajuste]
            
            query = f"INSERT INTO guild_config (guild_id, {columna}) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET {columna} = excluded.{columna}"
            await db_service.execute(query, (guild_id, canal.id))
            
            await ctx.reply(embed=embed_service.success(f"{ajuste}", f"✅ Canal configurado: {canal.mention}"))

async def setup(bot: commands.Bot):
    await bot.add_cog(Configuracion(bot))