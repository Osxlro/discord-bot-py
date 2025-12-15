import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal, Optional
from services import db_service, embed_service

class Configuracion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

    @commands.hybrid_group(name="setup", description="Configuraciones del Servidor")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

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

    # --- SUB-COMANDO: MENSAJES (ACTUALIZADO) ---
    @setup.command(name="mensajes", description="Personaliza las respuestas del bot en este servidor")
    @app_commands.describe(
        tipo="Tipo de mensaje", 
        texto="Tu mensaje. Variables: {user}, {level} (nivel). 'reset' para borrar."
    )
    async def setup_mensajes(self, ctx: commands.Context, tipo: Literal["Respuesta Mención", "Subida Nivel", "Felicitación Cumple"], texto: str):
        
        # Mapa de columnas
        if tipo == "Respuesta Mención": columna = "mention_response"
        elif tipo == "Subida Nivel": columna = "server_level_msg"
        else: columna = "server_birthday_msg"

        valor = None if texto.lower() == "reset" else texto
        
        await db_service.execute(f"""
            INSERT INTO guild_config (guild_id, {columna}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {columna} = excluded.{columna}
        """, (ctx.guild.id, valor))
        
        await ctx.reply(embed=embed_service.success(f"Configuración: {tipo}", "✅ Mensaje actualizado."))
        
    # --- SUB-COMANDO: CHAOS ---
    @setup.command(name="chaos", description="Configura la Ruleta Rusa (Chaos)")
    @app_commands.describe(
        estado="Activar o desactivar",
        probabilidad="Porcentaje de riesgo (1-100). Ejemplo: 5 para 5%."
    )
    async def setup_chaos(self, ctx: commands.Context, estado: Literal["Activado", "Desactivado"], probabilidad: int):
        # Validación
        if probabilidad < 1 or probabilidad > 100:
            await ctx.reply("❌ La probabilidad debe ser un número entre 1 y 100.", ephemeral=True)
            return

        enabled = 1 if estado == "Activado" else 0
        prob_decimal = probabilidad / 100.0 # Convertimos 5 a 0.05

        await db_service.execute("""
            INSERT INTO guild_config (guild_id, chaos_enabled, chaos_probability) VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                chaos_enabled = excluded.chaos_enabled,
                chaos_probability = excluded.chaos_probability
        """, (ctx.guild.id, enabled, prob_decimal))
        
        msg_estado = "✅ Activado" if enabled else "⚪ Desactivado"
        embed = embed_service.success("Configuración Chaos", f"{msg_estado}\n🔫 Probabilidad de disparo: **{probabilidad}%**")
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Configuracion(bot))