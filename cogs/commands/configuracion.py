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

async def setup(bot):
    await bot.add_cog(Configuracion(bot))