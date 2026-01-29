import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services import db_service, embed_service, lang_service

class Configuracion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- COMANDO SETUP (CENTRALIZADO) ---
    @commands.hybrid_command(name="setup", description="Configura canales y opciones del servidor.")
    @app_commands.describe(tipo="Qué configurar", canal="Canal (si aplica)", valor="Valor extra (opcional)")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context, 
                    tipo: Literal["Bienvenida", "Confesiones", "Logs", "Cumpleaños", "Idioma"], 
                    canal: discord.TextChannel = None, 
                    valor: str = None):
        
        updates = {}
        
        # Mapeo de lógica
        if tipo == "Bienvenida":
            if not canal: return await ctx.send("❌ Menciona un canal.")
            updates["welcome_channel_id"] = canal.id
            val_display = canal.mention
            
        elif tipo == "Confesiones":
            if not canal: return await ctx.send("❌ Menciona un canal.")
            updates["confessions_channel_id"] = canal.id
            val_display = canal.mention
            
        elif tipo == "Logs":
            if not canal: return await ctx.send("❌ Menciona un canal.")
            updates["logs_channel_id"] = canal.id
            val_display = canal.mention

        elif tipo == "Cumpleaños":
            if not canal: return await ctx.send("❌ Menciona un canal.")
            updates["birthday_channel_id"] = canal.id
            val_display = canal.mention

        elif tipo == "Idioma":
            if not valor or valor.lower() not in ["es", "en"]:
                return await ctx.send("❌ Idiomas válidos: `es`, `en`.")
            updates["language"] = valor.lower()
            val_display = valor.upper()

        # --- AQUÍ USAMOS LA FUNCIÓN OPTIMIZADA ---
        await db_service.update_guild_config(ctx.guild.id, updates)
        
        # Confirmación
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        msg = lang_service.get_text("setup_desc", lang, type=tipo, value=val_display)
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg))

    # --- SIMULACIÓN (MANTENIDA) ---
    @commands.hybrid_command(name="simular", description="Prueba mensajes de eventos.")
    @commands.has_permissions(administrator=True)
    async def simular(self, ctx: commands.Context, evento: Literal["Bienvenida", "Nivel", "Cumpleaños"]):
        # Ahora usamos el caché para leer la config
        config = await db_service.get_guild_config(ctx.guild.id)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if evento == "Bienvenida":
            msg = f"👋 **Simulación:** Bienvenido {ctx.author.mention}!"
            await ctx.send(msg)
            
        elif evento == "Nivel":
            txt = config.get('server_level_msg') or "¡{user} subió a nivel {level}!"
            final = txt.replace("{user}", ctx.author.mention).replace("{level}", "50")
            await ctx.send(f"🆙 **Simulación:** {final}")
            
        elif evento == "Cumpleaños":
            txt = config.get('server_birthday_msg') or "Feliz cumple {user}!"
            final = txt.replace("{user}", ctx.author.mention)
            await ctx.send(f"🎂 **Simulación:** {final}")

async def setup(bot):
    await bot.add_cog(Configuracion(bot))