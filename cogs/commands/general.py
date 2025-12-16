import discord
from discord.ext import commands
from discord import app_commands
from services import embed_service, translator_service, lang_service

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Context Menu (Click derecho en mensaje -> Apps -> Traducir)
        self.ctx_menu = app_commands.ContextMenu(name="Traducir", callback=self.traducir_mensaje)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.hybrid_command(name="ping", description="Chequea el Ping del Bot.")
    async def ping(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        ms = round(self.bot.latency * 1000)
        
        txt = lang_service.get_text("ping_msg", lang, ms=ms)
        await ctx.reply(embed=embed_service.info("Ping", txt))

    # --- COMANDO MEJORADO ---
    @commands.hybrid_command(name="calc", description="Calculadora flexible. Ej: /calc + 5 10")
    @app_commands.describe(
        operacion="Usa símbolos (+, -, *, /) o palabras (suma, resta...)", 
        num1="Primer número", 
        num2="Segundo número"
    )
    async def calc(self, ctx: commands.Context, operacion: str, num1: int, num2: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        # Diccionario de sinónimos: Mapea lo que escribe el usuario al símbolo matemático
        op_map = {
            "sumar": "+", "suma": "+", "add": "+", "+": "+", "mas": "+",
            "restar": "-", "resta": "-", "minus": "-", "-": "-", "menos": "-",
            "multiplicacion": "*", "multiplicar": "*", "por": "*", "*": "*", "x": "*",
            "division": "/", "dividir": "/", "div": "/", "/": "/"
        }
        
        # Convertimos a minúsculas y buscamos el símbolo
        op_symbol = op_map.get(operacion.lower())
        
        if not op_symbol:
            # Si no entiende la operación, avisamos qué símbolos acepta
            await ctx.reply(embed=embed_service.error("Error", "Operación no válida.\nUsa: `+`, `-`, `*`, `/`"), ephemeral=True)
            return
        
        try:
            # Lógica matemática directa (Adiós math_service)
            res = 0
            if op_symbol == "+": res = num1 + num2
            elif op_symbol == "-": res = num1 - num2
            elif op_symbol == "*": res = num1 * num2
            elif op_symbol == "/":
                if num2 == 0: raise ValueError("No puedes dividir por cero.")
                res = round(num1 / num2, 2)

            txt = lang_service.get_text("calc_result", lang, a=num1, op=op_symbol, b=num2, res=res)
            await ctx.reply(embed=embed_service.success("Math", txt))
            
        except ValueError as e:
            txt = lang_service.get_text("calc_error", lang, error=str(e))
            await ctx.reply(embed=embed_service.error("Error", txt, lite=True))

    async def traducir_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        lang = await lang_service.get_guild_lang(interaction.guild_id)
        await interaction.response.defer(ephemeral=True)
        
        try:
            res = await translator_service.traducir(message.content, "es")
            txt = lang_service.get_text("trans_result", lang, orig=message.content[:50]+"...", trans=res['traducido'])
            await interaction.followup.send(embed=embed_service.success("Traducir", txt), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))