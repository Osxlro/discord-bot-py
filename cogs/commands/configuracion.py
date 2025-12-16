import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal, Optional
from services import db_service, embed_service,lang_service

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

    # --- NUEVO: IDIOMA ---
    @setup.command(name="idioma", description="Change bot language / Cambiar idioma")
    @app_commands.describe(lenguaje="Español (es) or English (en)")
    async def setup_lang(self, ctx: commands.Context, lenguaje: Literal["es", "en"]):
        await db_service.execute("""
            INSERT INTO guild_config (guild_id, language) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET language = excluded.language
        """, (ctx.guild.id, lenguaje))
        
        # Respondemos en el idioma seleccionado
        msg = lang_service.get_text("lang_success", lenguaje)
        await ctx.reply(embed=embed_service.success("Idioma/Language", msg))
    
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
        tipo="Tipo de mensaje a configurar", 
        texto="Tu mensaje. Variables: {user}, {reason} (solo kick/ban). 'reset' para borrar."
    )
    async def setup_mensajes(self, ctx: commands.Context, tipo: Literal["Respuesta Mención", "Subida Nivel", "Felicitación Cumple", "Mensaje Kick", "Mensaje Ban"], texto: str):
        
        # Mapa de columnas actualizado
        mapa_columnas = {
            "Respuesta Mención": "mention_response",
            "Subida Nivel": "server_level_msg",
            "Felicitación Cumple": "server_birthday_msg",
            "Mensaje Kick": "server_kick_msg",
            "Mensaje Ban": "server_ban_msg"
        }
        columna = mapa_columnas[tipo]

        valor = None if texto.lower() == "reset" else texto
        
        await db_service.execute(f"""
            INSERT INTO guild_config (guild_id, {columna}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {columna} = excluded.{columna}
        """, (ctx.guild.id, valor))
        
        await ctx.reply(embed=embed_service.success(f"Configuración: {tipo}", "✅ Mensaje actualizado.", lite=True))
        
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
        prob_decimal = probabilidad / 100.0

        # 1. Guardar en Base de Datos (Persistencia)
        await db_service.execute("""
            INSERT INTO guild_config (guild_id, chaos_enabled, chaos_probability) VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                chaos_enabled = excluded.chaos_enabled,
                chaos_probability = excluded.chaos_probability
        """, (ctx.guild.id, enabled, prob_decimal))
        
        # 2. Actualizar Caché en Memoria (Velocidad)
        chaos_cog = self.bot.get_cog("Chaos")
        if chaos_cog:
            chaos_cog.update_local_config(ctx.guild.id, bool(enabled), prob_decimal)
        
        msg_estado = "✅ Activado" if enabled else "⚪ Desactivado"
        embed = embed_service.success("Configuración Chaos", f"{msg_estado}\n🔫 Probabilidad de disparo: **{probabilidad}%**")
        await ctx.reply(embed=embed)


    # --- COMANDO NUEVO: RESET ---
    @setup.command(name="reset", description="Desactiva una configuración del servidor.")
    @app_commands.describe(tipo="¿Qué configuración quieres borrar/resetear?")
    async def setup_reset(self, ctx: commands.Context, tipo: Literal["Bienvenidas", "Logs", "Confesiones", "Cumpleaños", "AutoRol", "Mensaje Nivel", "Mensajes Mod"]):
        
        mapa = {
            "Bienvenidas": "welcome_channel_id",
            "Logs": "logs_channel_id",
            "Confesiones": "confessions_channel_id",
            "Cumpleaños": "birthday_channel_id",
            "AutoRol": "autorole_id",
            "Mensaje Nivel": "server_level_msg",
        }
        
        if tipo == "Mensajes Mod":
             await db_service.execute(f"UPDATE guild_config SET server_kick_msg = NULL, server_ban_msg = NULL WHERE guild_id = ?", (ctx.guild.id,))
             await ctx.reply(embed=embed_service.success("Reset", "🗑️ Mensajes de moderación reseteados.", lite=True))
             return

        columna = mapa.get(tipo)
        await db_service.execute(f"UPDATE guild_config SET {columna} = 0 WHERE guild_id = ?", (ctx.guild.id,))
        await ctx.reply(embed=embed_service.success("Reset Completado", f"🗑️ La configuración de **{tipo}** ha sido eliminada.", lite=True))

    # --- COMANDO NUEVO: GESTIÓN DE ESTADOS ---
    @setup.command(name="status", description="Agrega o elimina estados del bot (Global).")
    @app_commands.describe(accion="Agregar o Eliminar", tipo="Tipo (Solo para agregar)", texto="Texto del estado")
    @commands.is_owner() # ¡Importante! Solo tú deberías tocar esto
    async def setup_status(self, ctx: commands.Context, accion: Literal["Agregar", "Eliminar", "Listar"], tipo: Literal["playing", "watching", "listening"] = "playing", texto: str = None):
        
        if accion == "Listar":
            rows = await db_service.fetch_all("SELECT id, type, text FROM bot_statuses")
            txt = "\n".join([f"`#{r['id']}` **{r['type']}** {r['text']}" for r in rows])
            await ctx.reply(embed=embed_service.info("Estados Activos", txt or "Ninguno."))
            return

        if not texto:
            await ctx.reply("❌ Necesitas escribir el texto del estado.", ephemeral=True)
            return

        if accion == "Agregar":
            await db_service.execute("INSERT INTO bot_statuses (type, text) VALUES (?, ?)", (tipo, texto))
            await ctx.reply(embed=embed_service.success("Estado Agregado", f"✅ Nuevo estado: **{tipo}** {texto}"))
            # Forzamos actualización visual inmediata
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=texto))
        
        elif accion == "Eliminar":
            # Intentamos borrar por texto exacto o por ID si el usuario puso un número
            try:
                if texto.isdigit():
                    await db_service.execute("DELETE FROM bot_statuses WHERE id = ?", (int(texto),))
                else:
                    await db_service.execute("DELETE FROM bot_statuses WHERE text = ?", (texto,))
                await ctx.reply(embed=embed_service.success("Estado Eliminado", "🗑️ Estado borrado de la rotación."))
            except Exception as e:
                await ctx.reply(f"Error: {e}")
    
async def setup(bot: commands.Bot):
    await bot.add_cog(Configuracion(bot))