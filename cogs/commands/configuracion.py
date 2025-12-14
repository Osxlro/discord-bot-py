import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal, Optional
from services import db_service, embed_service

class Configuracion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- COMANDO PREFIX (Fuera del grupo setup) ---
    @commands.hybrid_command(name="prefix", description="Cambia tu prefijo personal para comandos de texto")
    async def set_prefix(self, ctx: commands.Context, nuevo: str):
        if len(nuevo) > 5:
            await ctx.reply("Máximo 5 caracteres.", ephemeral=True)
            return

        row = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        if not row:
            await db_service.execute("INSERT INTO users (user_id, custom_prefix) VALUES (?, ?)", (ctx.author.id, nuevo))
        else:
            await db_service.execute("UPDATE users SET custom_prefix = ? WHERE user_id = ?", (nuevo, ctx.author.id))
            
        await ctx.reply(embed=embed_service.success("Prefijo Personal", f"Nuevo prefijo: `{nuevo}`"))

    # --- GRUPO PRINCIPAL: SETUP (Ahora es Hybrid para salir en Help) ---
    @commands.hybrid_group(name="setup", description="Configuraciones del Servidor")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context):
        # Si el usuario escribe solo "/setup" sin subcomando, le mostramos la ayuda
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    # --- SUB-COMANDO: CANALES ---
    @setup.command(name="canales", description="Configura los canales de bienvenida, logs, etc.")
    @app_commands.describe(tipo="¿Qué canal quieres configurar?", canal="El canal de texto")
    async def setup_canales(self, ctx: commands.Context, tipo: Literal["Bienvenidas", "Logs", "Confesiones", "Cumpleaños"], canal: discord.TextChannel):
        col_map = {
            "Bienvenidas": "welcome_channel_id",
            "Logs": "logs_channel_id",
            "Confesiones": "confessions_channel_id",
            "Cumpleaños": "birthday_channel_id"
        }
        columna = col_map[tipo]
        
        await db_service.execute(f"""
            INSERT INTO guild_config (guild_id, {columna}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {columna} = excluded.{columna}
        """, (ctx.guild.id, canal.id))
        
        embed = embed_service.success(f"Canal de {tipo}", f"✅ Configurado exitosamente en: {canal.mention}")
        await ctx.reply(embed=embed)

    # --- SUB-COMANDO: ROLES ---
    @setup.command(name="autorol", description="Define el rol que se da al entrar")
    @app_commands.describe(rol="Rol para nuevos usuarios (o vacío para desactivar)")
    async def setup_autorol(self, ctx: commands.Context, rol: Optional[discord.Role] = None):
        if rol:
            if rol.position >= ctx.guild.me.top_role.position:
                await ctx.reply("❌ Ese rol es superior al mío, no puedo darlo.", ephemeral=True)
                return
            valor = rol.id
            msg = f"✅ Auto-Rol activado: {rol.mention}"
        else:
            valor = 0
            msg = "⚪ Auto-Rol desactivado."

        await db_service.execute("""
            INSERT INTO guild_config (guild_id, autorole_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET autorole_id = excluded.autorole_id
        """, (ctx.guild.id, valor))
        
        await ctx.reply(embed=embed_service.success("Auto Rol", msg))

    # --- SUB-COMANDO: MENSAJES ---
    @setup.command(name="mensajes", description="Personaliza las respuestas del bot en este servidor")
    @app_commands.describe(tipo="Mención o Nivel", texto="Tu mensaje (Usa {user}, {level}). Escribe 'reset' para borrar.")
    async def setup_mensajes(self, ctx: commands.Context, tipo: Literal["Respuesta Mención", "Subida Nivel"], texto: str):
        columna = "mention_response" if tipo == "Respuesta Mención" else "server_level_msg"
        valor = None if texto.lower() == "reset" else texto
        
        await db_service.execute(f"""
            INSERT INTO guild_config (guild_id, {columna}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {columna} = excluded.{columna}
        """, (ctx.guild.id, valor))
        
        await ctx.reply(embed=embed_service.success(f"Configuración: {tipo}", "✅ Mensaje actualizado."))

async def setup(bot: commands.Bot):
    await bot.add_cog(Configuracion(bot))