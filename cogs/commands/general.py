import discord
from discord.ext import commands
from discord import app_commands
from services import embed_service, translator_service, db_service  # Asegúrate de importar el servicio

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

    # --- COMANDO: TRADUCIR ---
    @commands.hybrid_command(name="traducir", description="Traduce un texto a otro idioma (ej: en, fr, it, ja)")
    @app_commands.describe(texto="Lo que quieres traducir", idioma="Código del idioma destino (por defecto: es)")
    async def traducir(self, ctx: commands.Context, texto: str, idioma: str = "es"):
        # 1. Indicamos que estamos pensando
        await ctx.defer() 
        
        try:
            resultado = await translator_service.traducir(texto, idioma)
            
            embed = embed_service.info(
                "Traducción",
                f"**Original:** {resultado['original']}\n"
                f"**Traducido ({idioma}):** {resultado['traducido']}"
            )
            
            # 2. CORRECCIÓN AQUÍ:
            # Usamos ctx.send() en lugar de ctx.followup.send()
            # En comandos híbridos, ctx.send() actúa inteligentemente como followup si ya hubo defer.
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(embed=embed_service.error("Error", str(e)))
    async def traducir_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        # Aquí SÍ usamos interaction, por lo tanto SÍ usamos followup
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

    @commands.hybrid_command(name="setprefix", description="Cambia el prefijo que usas con el bot")
    async def setprefix(self, ctx: commands.Context, nuevo_prefix: str):
        if len(nuevo_prefix) > 5:
            await ctx.reply("El prefijo no puede tener más de 5 caracteres.", ephemeral=True)
            return

        # Guardamos en la tabla de usuarios
        # Asegúrate de que db_service.execute usa INSERT OR REPLACE o similar lógica si el usuario no existe
        # Como usamos UPDATE o INSERT, haremos un truco de SQLite moderno:
        
        # Primero verificamos si existe
        check = await db_service.fetch_one("SELECT user_id FROM users WHERE user_id = ?", (ctx.author.id,))
        
        if not check:
            await db_service.execute("INSERT INTO users (user_id, custom_prefix) VALUES (?, ?)", (ctx.author.id, nuevo_prefix))
        else:
            await db_service.execute("UPDATE users SET custom_prefix = ? WHERE user_id = ?", (nuevo_prefix, ctx.author.id))
            
        embed = embed_service.success("Prefijo Actualizado", f"Ahora puedes usarme con: `{nuevo_prefix}` (ej: `{nuevo_prefix}ping`)")
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))