import discord
from discord.ext import commands
from discord import app_commands
from services.features import diversion_service
from services.core import lang_service
from services.utils import embed_service

class Diversion(commands.Cog):
    """
    Cog de entretenimiento y minijuegos.
    Contiene comandos para interactuar con emojis, azar, confesiones y juegos clásicos.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="jumbo", description="Muestra la imagen de un emoji en grande.")
    @app_commands.describe(emoji="Pon aquí el emoji personalizado")
    async def jumbo(self, ctx: commands.Context, emoji: str):
        """Amplía un emoji personalizado para ver su imagen en alta resolución."""
        # Obtener idioma del servidor o global
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Delegar el procesamiento del emoji al servicio
        embed, error = await diversion_service.handle_jumbo(emoji, lang)
        
        if error:
            # Responder con error si el emoji no es válido o no es personalizado
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
        
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="coinflip", description="Lanza una moneda.")
    async def coinflip(self, ctx: commands.Context):
        """Simula el lanzamiento de una moneda (Cara o Cruz)."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # Obtener el embed con el resultado y el GIF correspondiente desde el servicio
        embed = diversion_service.handle_coinflip(lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="choice", description="Elige entre dos opciones.")
    async def eleccion(self, ctx: commands.Context, opcion_a: str, opcion_b: str):
        """Ayuda al usuario a decidir entre dos opciones dadas."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio elige una opción al azar y construye el embed
        embed = diversion_service.handle_choice(opcion_a, opcion_b, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="emojimix", description="Mezcla dos emojis.")
    async def emojimix(self, ctx: commands.Context, emoji1: str, emoji2: str):
        """Combina dos emojis usando la API de Google Emoji Kitchen."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio genera la URL de la imagen combinada
        embed = diversion_service.handle_emojimix(emoji1, emoji2, lang)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="confess", description="Confesión anónima.")
    @app_commands.describe(secreto="Tu secreto.")
    async def confesar(self, ctx: commands.Context, *, secreto: str):
        """Envía un mensaje anónimo a un canal de confesiones configurado."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio verifica la configuración del servidor y prepara el embed anónimo
        channel_id, embed, error = await diversion_service.handle_confess(ctx.guild.id if ctx.guild else None, secreto, lang)
        
        if error:
            # Error si el canal no está configurado
            return await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), error, lite=True), ephemeral=True)
            
        # Obtener el objeto del canal de Discord
        canal = self.bot.get_channel(channel_id)
        if not canal: return

        try:
            # Enviar la confesión al canal destino
            await canal.send(embed=embed)
            # Confirmar al usuario de forma efímera
            msg = lang_service.get_text("confess_sent", lang, channel=canal.mention)
            await ctx.reply(embed=embed_service.success(lang_service.get_text("title_success", lang), msg, lite=True), ephemeral=True)
        except discord.Forbidden:
            # Error si el bot no tiene permisos de escritura en el canal de confesiones
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("confess_error_perms", lang), lite=True), ephemeral=True)

    @commands.hybrid_command(name="8ball", description="Pregúntale a la bola mágica.")
    @app_commands.describe(pregunta="Tu pregunta")
    async def eightball(self, ctx: commands.Context, pregunta: str):
        """Responde a una pregunta con una de las respuestas clásicas de la bola 8."""
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        
        # El servicio elige una respuesta aleatoria localizada
        embed = diversion_service.handle_8ball(pregunta, lang)
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    """Función de entrada para cargar el Cog en el bot."""
    await bot.add_cog(Diversion(bot))