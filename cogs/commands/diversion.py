import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from services import embed_service, emojimixer_service, random_service, db_service, lang_service

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
                    description="Aquí tienes tu emoji en tamaño completo:",
                    lite=True
                )
                # Ponemos la imagen del emoji en grande
                embed.set_image(url=partial_emoji.url)
                
                await ctx.reply(embed=embed)
            else:
                # Si es un emoji normal de texto (🍎, 😎), no tienen URL de imagen directa
                embed = embed_service.error(
                    title="Emoji no válido", 
                    description="Solo puedo hacer zoom a **emojis personalizados** del servidor (los que tienen imagen propia).",
                    lite=True
                )
                await ctx.reply(embed=embed, ephemeral=True)

        except Exception:
            # Si el usuario escribe algo que no es un emoji
            embed = embed_service.error(
                title="Error", 
                description="Eso no parece ser un emoji válido. Intenta poner solo un emoji.",
                lite=True
            )
            await ctx.reply(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="coinflip")
    async def coinflip(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        res, url_gif = random_service.obtener_cara_cruz()
        
        title = lang_service.get_text("coinflip_title", lang)
        desc = lang_service.get_text("coinflip_desc", lang, result=res)
        
        # ¡MIRA QUÉ LIMPIO! Pasamos el thumbnail directo a la función
        await ctx.reply(embed=embed_service.info(title, desc, thumbnail=url_gif, lite=True))

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
            description=f"Entre **{opcion_a}** y **{opcion_b}**, elijo:\n\n👉 **{eleccion}**",
            lite=True
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="emojimix")
    async def emojimix(self, ctx: commands.Context, emoji1: str, emoji2: str):
        url = emojimixer_service.generar_url_emojimix(emoji1, emoji2)
        await ctx.reply(embed=embed_service.info("Emoji Mix", f"{emoji1} + {emoji2}", image=url, lite=True))

    @app_commands.command(name="confess")
    async def confesar(self, interaction: discord.Interaction, secreto: str):
        lang = await lang_service.get_guild_lang(interaction.guild_id)
        row = await db_service.fetch_one("SELECT confessions_channel_id FROM guild_config WHERE guild_id = ?", (interaction.guild_id,))

        if not row or not row['confessions_channel_id']:
            await interaction.response.send_message("❌ No channel setup.", ephemeral=True)
            return

        canal = self.bot.get_channel(row['confessions_channel_id'])
        
        # Embed de confesión
        embed = discord.Embed(title=lang_service.get_text("confess_title", lang), description=f"\"{secreto}\"", color=discord.Color.random())
        embed.set_footer(text="Anon")
        await canal.send(embed=embed)

        # Confirmación
        msg = lang_service.get_text("confess_sent", lang, channel=canal.mention)
        await interaction.response.send_message(embed=embed_service.success("Sent", msg), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Diversion(bot))