import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services import db_service, embed_service, lang_service

class Configuracion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # SETUP
    @commands.hybrid_command(name="setup", description="Configura canales y opciones del servidor.")
    @app_commands.describe(tipo="Qué configurar", canal="Canal (si aplica)", valor="Valor extra (opcional)")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context, 
                    tipo: Literal["Bienvenida", "Confesiones", "Logs", "Cumpleaños", "Idioma"], 
                    canal: discord.TextChannel = None, 
                    valor: str = None):
        
        await ctx.defer(ephemeral=True)
        
        updates = {}
        
        # Procesar según el tipo
        if tipo == "Bienvenida":
            if not canal: return await ctx.send("❌ Menciona un canal.", ephemeral=True)
            updates["welcome_channel_id"] = canal.id
            val_display = canal.mention
            
        elif tipo == "Confesiones":
            if not canal: return await ctx.send("❌ Menciona un canal.", ephemeral=True)
            updates["confessions_channel_id"] = canal.id
            val_display = canal.mention
            
        elif tipo == "Logs":
            if not canal: return await ctx.send("❌ Menciona un canal.", ephemeral=True)
            updates["logs_channel_id"] = canal.id
            val_display = canal.mention

        elif tipo == "Cumpleaños":
            if not canal: return await ctx.send("❌ Menciona un canal.", ephemeral=True)
            updates["birthday_channel_id"] = canal.id
            val_display = canal.mention

        elif tipo == "Idioma":
            if not valor or valor.lower() not in ["es", "en"]:
                return await ctx.send("❌ Idiomas válidos: `es`, `en`.", ephemeral=True)
            updates["language"] = valor.lower()
            val_display = valor.upper()

        # Actualizar a la base de datos
        await db_service.update_guild_config(ctx.guild.id, updates)
        
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        msg = lang_service.get_text("setup_desc", lang, type=tipo, value=val_display)
        await ctx.send(embed=embed_service.success(lang_service.get_text("setup_success", lang), msg), ephemeral=True)

    # SIMULAR
    @commands.hybrid_command(name="simular", description="Prueba mensajes de eventos (Solo tú lo verás).")
    @commands.has_permissions(administrator=True)
    async def simular(self, ctx: commands.Context, evento: Literal["Bienvenida", "Nivel", "Cumpleaños"]):
        await ctx.defer(ephemeral=True)
        
        # Obtener configuración del servidor
        config = await db_service.get_guild_config(ctx.guild.id)
        
        # Simular según el evento
        if evento == "Bienvenida":
            msg = f"👋 **Simulación:** Bienvenido {ctx.author.mention}!"
            await ctx.send(msg, ephemeral=True)
            
        elif evento == "Nivel":
            txt = config.get('server_level_msg') or "¡{user} subió a nivel {level}!"
            final = txt.replace("{user}", ctx.author.mention).replace("{level}", "50")
            await ctx.send(f"🆙 **Simulación:** {final}", ephemeral=True)
            
        elif evento == "Cumpleaños":
            txt = config.get('server_birthday_msg') or "Feliz cumple {user}!"
            final = txt.replace("{user}", ctx.author.mention)
            await ctx.send(f"🎂 **Simulación:** {final}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Configuracion(bot))