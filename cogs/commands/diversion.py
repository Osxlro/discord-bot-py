import discord
from discord.ext import commands
from discord import app_commands
from services import embed_service, emojimixer_service, random_service, db_service, lang_service

class Diversion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="jumbo", description="Muestra la imagen de un emoji en grande")
    @app_commands.describe(emoji="Pon aquí el emoji personalizado que quieras ver")
    async def jumbo(self, ctx: commands.Context, emoji: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        try:
            partial_emoji = discord.PartialEmoji.from_str(emoji)
            if partial_emoji.is_custom_emoji():
                title = lang_service.get_text("jumbo_title", lang, name=partial_emoji.name)
                # Embed simplificado
                await ctx.reply(embed=embed_service.info(title, "", image=partial_emoji.url, lite=True))
            else:
                msg = lang_service.get_text("jumbo_error", lang)
                await ctx.reply(embed=embed_service.error("Error", msg, lite=True), ephemeral=True)
        except Exception:
            msg = lang_service.get_text("jumbo_invalid", lang)
            await ctx.reply(embed=embed_service.error("Error", msg, lite=True), ephemeral=True)

    @commands.hybrid_command(name="coinflip")
    async def coinflip(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        res, url_gif = random_service.obtener_cara_cruz()
        
        title = lang_service.get_text("coinflip_title", lang)
        desc = lang_service.get_text("coinflip_desc", lang, result=res)
        
        await ctx.reply(embed=embed_service.info(title, desc, thumbnail=url_gif, lite=True))

    @commands.hybrid_command(name="eleccion")
    async def eleccion(self, ctx: commands.Context, opcion_a: str, opcion_b: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        eleccion = random_service.elegir_opcion(opcion_a, opcion_b)
        
        title = lang_service.get_text("choice_title", lang)
        desc = lang_service.get_text("choice_desc", lang, a=opcion_a, b=opcion_b, result=eleccion)
        
        await ctx.reply(embed=embed_service.success(title, desc, lite=True))

    @commands.hybrid_command(name="emojimix")
    async def emojimix(self, ctx: commands.Context, emoji1: str, emoji2: str):
        url = emojimixer_service.generar_url_emojimix(emoji1, emoji2)
        await ctx.reply(embed=embed_service.info("Emoji Mix", f"{emoji1} + {emoji2}", image=url, lite=True))

    @app_commands.command(name="confess")
    async def confesar(self, interaction: discord.Interaction, secreto: str):
        lang = await lang_service.get_guild_lang(interaction.guild_id)
        row = await db_service.fetch_one("SELECT confessions_channel_id FROM guild_config WHERE guild_id = ?", (interaction.guild_id,))

        if not row or not row['confessions_channel_id']:
            await interaction.response.send_message("❌ Channel not setup.", ephemeral=True)
            return

        canal = self.bot.get_channel(row['confessions_channel_id'])
        if not canal: return

        title = lang_service.get_text("confess_title", lang)
        embed = discord.Embed(title=title, description=f"\"{secreto}\"", color=discord.Color.random())
        embed.set_footer(text="Anon")
        await canal.send(embed=embed)

        msg = lang_service.get_text("confess_sent", lang, channel=canal.mention)
        await interaction.response.send_message(embed=embed_service.success("Sent", msg), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Diversion(bot))