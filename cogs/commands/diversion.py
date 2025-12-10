import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from services import embed_service, emojimixer_service, random_service

class Diversion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- COMANDO: JUMBO (Agrandar Emoji) ---
    @commands.hybrid_command(name="jumbo", description="Muestra la imagen de un emoji en grande")
    @app_commands.describe(emoji="Pon aquí el emoji personalizado que quieras ver")
    async def zoom(self, ctx: commands.Context, emoji: str):
        try:
            # Intentamos convertir el texto (string) a un objeto Emoji de Discord
            partial_emoji = discord.PartialEmoji.from_str(emoji)

            # Verificamos si es un emoji personalizado (tiene ID)
            if partial_emoji.is_custom_emoji():
                # Creamos el embed usando tu servicio de diseños
                embed = embed_service.info(
                    title=f"Emoji: {partial_emoji.name}", 
                    description="Aquí tienes tu emoji en tamaño completo:"
                )
                # Ponemos la imagen del emoji en grande
                embed.set_image(url=partial_emoji.url)
                
                await ctx.reply(embed=embed)
            else:
                # Si es un emoji normal de texto (🍎, 😎), no tienen URL de imagen directa
                embed = embed_service.error(
                    title="Emoji no válido", 
                    description="Solo puedo hacer zoom a **emojis personalizados** del servidor (los que tienen imagen propia)."
                )
                await ctx.reply(embed=embed, ephemeral=True)

        except Exception:
            # Si el usuario escribe algo que no es un emoji
            embed = embed_service.error(
                title="Error", 
                description="Eso no parece ser un emoji válido. Intenta poner solo un emoji."
            )
            await ctx.reply(embed=embed, ephemeral=True)

    # --- COMANDO: COINFLIP (Cara o Cruz) ---
    @commands.hybrid_command(name="coinflip", description="Lanza una moneda al aire")
    async def coinflip(self, ctx: commands.Context):
        # Lógica en el servicio
        resultado, emoji = random_service.obtener_cara_cruz()
        
        embed = embed_service.info(
            title="Moneda lanzada",
            description=f"La moneda ha caído en: **{resultado}** {emoji}"
        )
        await ctx.reply(embed=embed)

    # --- COMANDO: CHOOSER (Elige por ti) ---
    @commands.hybrid_command(name="eleccion", description="¿Indeciso? El bot elige entre dos opciones por ti")
    @app_commands.describe(
        opcion_a="La primera opción",
        opcion_b="La segunda opción"
    )
    async def eleccion(self, ctx: commands.Context, opcion_a: str, opcion_b: str):
        # Lógica en el servicio
        eleccion = random_service.elegir_opcion(opcion_a, opcion_b)
        
        embed = embed_service.success(
            title="He tomado una decisión",
            description=f"Entre **{opcion_a}** y **{opcion_b}**, elijo:\n\n👉 **{eleccion}**"
        )
        await ctx.reply(embed=embed)

    # --- COMANDO: EMOJIMIX (Mezclador) ---
    @commands.hybrid_command(name="emojimix", description="Mezcla dos emojis (Estilo Google Emoji Kitchen)")
    @app_commands.describe(emoji1="Primer emoji", emoji2="Segundo emoji")
    async def emojimix(self, ctx: commands.Context, emoji1: str, emoji2: str):
        
        # Generamos la URL
        url_imagen = emojimixer_service.generar_url_emojimix(emoji1, emoji2)
        
        embed = embed_service.info("Emoji Kitchen", f"Mezcla de {emoji1} + {emoji2}")
        embed.set_image(url=url_imagen)
        
        await ctx.reply(embed=embed)

    # --- COMANDO: CONFESAR (Confiesa tus pecados) ---
    @app_commands.command(name="confess", description="Envía un secreto anónimo al servidor")
    @app_commands.describe(secreto="Tu confesión anónima (¡Nadie sabrá que fuiste tú!)")
    async def confesar(self, interaction: discord.Interaction, secreto: str):
        # 1. Obtener el ID desde la configuración
        canal_id = settings.CONFIG["channels"].get("confessions_channel_id")

        # 2. Validaciones básicas
        if not canal_id:
            embed = embed_service.error(
                "Configuración Faltante", 
                "El dueño del bot no ha configurado el ID del canal de confesiones en `config.json`."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        canal = self.bot.get_channel(canal_id)
        if not canal:
            embed = embed_service.error(
                "Error de Canal", 
                f"No encuentro el canal con ID `{canal_id}`. Verifica que el bot tenga acceso."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 3. Construir la confesión (Estética anónima)
        embed_confesion = discord.Embed(
            title="🤫 Nueva Confesión Anónima",
            description=f"\"{secreto}\"",
            color=discord.Color.random() # Color aleatorio para cada confesión
        )
        # Usamos el footer global que ya configuraste en embed_service, 
        # o forzamos uno personalizado para que se entienda la mecánica:
        embed_confesion.set_footer(text="Enviado de forma anónima vía /confesar")

        # 4. Enviar al canal público
        await canal.send(embed=embed_confesion)

        # 5. Confirmación privada al usuario
        embed_confirm = embed_service.success(
            "Confesión Enviada", 
            f"Tu secreto ha sido publicado en {canal.mention}. 🤐"
        )
        await interaction.response.send_message(embed=embed_confirm, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Diversion(bot))