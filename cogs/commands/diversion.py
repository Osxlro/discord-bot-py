import discord
import random
from discord.ext import commands
from discord import app_commands
from services import embed_service, emojimixer_service, random_service, db_service, lang_service

class Diversion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="jumbo", description="Muestra la imagen de un emoji en grande.")
    @app_commands.describe(emoji="Pon aquí el emoji personalizado")
    async def jumbo(self, ctx: commands.Context, emoji: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        try:
            partial_emoji = discord.PartialEmoji.from_str(emoji)
            if partial_emoji.is_custom_emoji():
                title = lang_service.get_text("jumbo_title", lang, name=partial_emoji.name)
                await ctx.reply(embed=embed_service.info(title, "", image=partial_emoji.url))
            else:
                msg = lang_service.get_text("jumbo_error", lang)
                await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), msg, lite=True), ephemeral=True)
        except Exception:
            msg = lang_service.get_text("jumbo_invalid", lang)
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), msg, lite=True), ephemeral=True)

    @commands.hybrid_command(name="coinflip", description="Lanza una moneda.")
    async def coinflip(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        res, url_gif = random_service.obtener_cara_cruz()
        
        title = lang_service.get_text("coinflip_title", lang)
        desc = lang_service.get_text("coinflip_desc", lang, result=res)
        
        await ctx.reply(embed=embed_service.info(title, desc, thumbnail=url_gif, lite=True))

    @commands.hybrid_command(name="eleccion", description="Elige entre dos opciones.")
    async def eleccion(self, ctx: commands.Context, opcion_a: str, opcion_b: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        eleccion = random_service.elegir_opcion(opcion_a, opcion_b)
        
        title = lang_service.get_text("choice_title", lang)
        desc = lang_service.get_text("choice_desc", lang, a=opcion_a, b=opcion_b, result=eleccion)
        
        await ctx.reply(embed=embed_service.success(title, desc, lite=True))

    @commands.hybrid_command(name="emojimix", description="Mezcla dos emojis.")
    async def emojimix(self, ctx: commands.Context, emoji1: str, emoji2: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        url = emojimixer_service.generar_url_emojimix(emoji1, emoji2)
        await ctx.reply(embed=embed_service.info(lang_service.get_text("emojimix_title", lang), f"{emoji1} + {emoji2}", image=url))

    @commands.hybrid_command(name="confess", description="Confesión anónima.")
    @app_commands.describe(secreto="Tu secreto.")
    async def confesar(self, ctx: commands.Context, *, secreto: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        config = await db_service.get_guild_config(ctx.guild.id if ctx.guild else None)
        channel_id = config.get('confessions_channel_id')

        if not channel_id:
            await ctx.reply(
                embed=embed_service.error(lang_service.get_text("title_error", lang), "❌ Canal de confesiones no establecido.", lite=True), 
                ephemeral=True
            )
            return

        canal = self.bot.get_channel(channel_id)
        if not canal: return

        title = lang_service.get_text("confess_title", lang)
        embed = discord.Embed(title=title, description=f"\"{secreto}\"", color=discord.Color.random())
        embed.set_footer(text=lang_service.get_text("confess_anon", lang))
        
        try:
            await canal.send(embed=embed)
            msg = lang_service.get_text("confess_sent", lang, channel=canal.mention)
            await ctx.reply(embed=embed_service.success(lang_service.get_text("title_success", lang), msg, lite=True), ephemeral=True)
        except discord.Forbidden:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), "❌ No tengo permisos para enviar mensajes en ese canal.", lite=True), ephemeral=True)
        except Exception as e:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), f"Error: {e}", lite=True), ephemeral=True)

    @commands.hybrid_command(name="8ball", description="Pregúntale a la bola mágica.")
    @app_commands.describe(pregunta="Tu pregunta")
    async def eightball(self, ctx: commands.Context, pregunta: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id if ctx.guild else None)
        respuestas = lang_service.get_text("8ball_responses", lang).split("|")
        respuesta = random.choice(respuestas)
        await ctx.reply(embed=embed_service.info("🎱 8-Ball", f"**P:** {pregunta}\n**R:** {respuesta}", lite=True))

async def setup(bot: commands.Bot):
    await bot.add_cog(Diversion(bot))