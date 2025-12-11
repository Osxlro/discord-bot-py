import discord
from discord.ext import commands
from discord import app_commands
from services import embed_service, translator_service, db_service

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
    @commands.hybrid_command(name="ping", description="Muestra la latencia del bot")
    async def ping(self, ctx: commands.Context):
        latencia = round(self.bot.latency * 1000)
        embed = embed_service.info("Ping", f"🏓 Pong! Latencia: **{latencia}ms**")
        await ctx.reply(embed=embed)

    # --- COMANDO: AVATAR ---
    @commands.hybrid_command(name="avatar", description="Muestra el avatar de un usuario")
    async def avatar(self, ctx: commands.Context, usuario: discord.Member = None):
        usuario = usuario or ctx.author
        embed = embed_service.info(f"Avatar de {usuario.name}", "")
        embed.set_image(url=usuario.display_avatar.url)
        await ctx.reply(embed=embed)

    # --- COMANDO: TRADUCIR (Híbrido) ---
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

    # --- CALLBACK DEL MENÚ CONTEXTUAL ---
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

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))