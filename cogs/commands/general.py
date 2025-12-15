import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import embed_service, translator_service, math_service, db_service, lang_service

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # --- MENÚ CONTEXTUAL (Click Derecho -> Apps -> Traducir) ---
        self.ctx_menu = app_commands.ContextMenu(
            name="Traducir a Español",
            callback=self.traducir_mensaje
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        # Si descargamos el cog, quitamos el menú para no duplicarlo
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    # --- COMANDO: PING ---
    async def ping(self, ctx: commands.Context):
        # 1. Obtener idioma del servidor (esto se puede optimizar cacheando, pero por ahora select)
        row = await db_service.fetch_one("SELECT language FROM guild_config WHERE guild_id = ?", (ctx.guild.id,))
        lang = row['language'] if row else "es"

        latencia = round(self.bot.latency * 1000)
    
        # 2. Obtener texto traducido
        texto = lang_service.get_text("ping_msg", lang=lang, ms=latencia)
    
        # 3. Embed en una línea
        await ctx.reply(embed=embed_service.info("Ping", texto))

    # --- COMANDO: AVATAR ---
    @commands.hybrid_command(name="avatar", description="Muestra el avatar de un usuario")
    async def avatar(self, ctx: commands.Context, usuario: discord.Member = None):
        usuario = usuario or ctx.author
        embed = embed_service.info(f"Avatar de {usuario.name}", "")
        embed.set_image(url=usuario.display_avatar.url)
        await ctx.reply(embed=embed)

    # --- COMANDO: TRADUCIR ---
    @commands.hybrid_command(name="traducir", description="Traduce un texto a otro idioma (ej: en, fr, it, ja)")
    @app_commands.describe(texto="Lo que quieres traducir", idioma="Código del idioma destino (por defecto: es)")
    async def traducir(self, ctx: commands.Context, texto: str, idioma: str = "es"):
        await ctx.defer() 
        try:
            resultado = await translator_service.traducir(texto, idioma)
            embed = embed_service.info(
                "Traducción",
                f"**Original:** {resultado['original']}\n"
                f"**Traducido ({idioma}):** {resultado['traducido']}"
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(embed=embed_service.error("Error", str(e)))

    async def traducir_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        if not message.content:
            await interaction.followup.send("❌ Ese mensaje no tiene texto.", ephemeral=True)
            return
        try:
            resultado = await translator_service.traducir(message.content, "es")
            embed = embed_service.success(
                "Traducción Rápida",
                f"**De:** {message.author.mention}\n"
                f"**Dice:** {resultado['traducido']}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error al traducir: {e}", ephemeral=True)
    
    # --- COMANDO: MATEMATICAS ---
    @commands.hybrid_command(name="calc", description="Calculadora simple")
    @app_commands.describe(operacion="Operación", num1="Número 1", num2="Número 2")
    async def calc(self, ctx: commands.Context, operacion: Literal["sumar", "restar", "multiplicacion", "division"], num1: int, num2: int):
        try:
            res = math_service.calcular(operacion, num1, num2)
            op_emojis = {"sumar": "➕", "restar": "➖", "multiplicacion": "✖️", "division": "➗"}
            
            embed = embed_service.success("Resultado", f"{op_emojis.get(operacion)} `{num1}` y `{num2}` = **{res}**")
            await ctx.reply(embed=embed)
        except ValueError as e:
            await ctx.reply(embed=embed_service.error("Error Matemático", str(e)), ephemeral=True)

    # CONTEXT MENU
    # TRADUCIR
    async def traducir_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        if not message.content:
            await interaction.followup.send("❌ Sin texto.", ephemeral=True)
            return
        try:
            res = await translator_service.traducir(message.content, "es")
            embed = embed_service.success("Traducción Rápida", f"**De:** {message.author.mention}\n**Dice:** {res['traducido']}")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))