import discord
from discord.ext import commands
from discord import app_commands
from services import db_service, embed_service

class Configuracion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- COMANDO 1: Configurar Prefijo Personal (Movido desde General) ---
    @commands.hybrid_command(name="setprefix", description="Cambia el prefijo que usas con el bot")
    @app_commands.describe(nuevo_prefix="El nuevo símbolo (máx 5 caracteres)")
    async def setprefix(self, ctx: commands.Context, nuevo_prefix: str):
        if len(nuevo_prefix) > 5:
            await ctx.reply("El prefijo no puede tener más de 5 caracteres.", ephemeral=True)
            return

        # Verificamos si ya existe el usuario
        check = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        
        if not check:
            await db_service.execute("INSERT INTO users (user_id, custom_prefix) VALUES (?, ?)", (ctx.author.id, nuevo_prefix))
        else:
            await db_service.execute("UPDATE users SET custom_prefix = ? WHERE user_id = ?", (nuevo_prefix, ctx.author.id))
            
        embed = embed_service.success("Prefijo Actualizado", f"Ahora puedes usarme con: `{nuevo_prefix}` (ej: `{nuevo_prefix}ping`)")
        await ctx.reply(embed=embed)

    # --- COMANDO 2: Configurar Respuesta a Mención (Nuevo) ---
    @commands.hybrid_command(name="setmencion", description="Define qué responde el bot al ser mencionado (@Bot)")
    @app_commands.describe(mensaje="El mensaje de respuesta (escribe 'reset' para borrar)")
    @commands.has_permissions(administrator=True) # Solo admins pueden cambiar la config del servidor
    async def setmencion(self, ctx: commands.Context, mensaje: str):
        if mensaje.lower() == "reset":
            nuevo_valor = None
            texto_confirm = "El mensaje de mención ha sido restablecido al valor por defecto."
        else:
            nuevo_valor = mensaje
            texto_confirm = f"✅ Ahora responderé: **{mensaje}**"

        # Guardamos en la tabla del SERVIDOR (guild_config)
        # Usamos UPSERT para crear la fila del servidor si no existe
        await db_service.execute("""
            INSERT INTO guild_config (guild_id, mention_response) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET mention_response = excluded.mention_response
        """, (ctx.guild.id, nuevo_valor))

        embed = embed_service.success("Configuración de Servidor", texto_confirm)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Configuracion(bot))