import discord
import logging
from discord import app_commands
from discord.ext import commands
from services import embed_service, translator_service, lang_service

logger = logging.getLogger(__name__)

class HelpSelect(discord.ui.Select):
    def __init__(self, bot, ctx, lang):
        self.bot = bot
        self.ctx = ctx
        self.lang = lang
        
        options = [
            discord.SelectOption(
                label=lang_service.get_text("help_home", lang),
                description=lang_service.get_text("help_home_desc", lang),
                value="home",
                emoji="🏠"
            )
        ]

        emoji_map = {
            "General": "💡", "Moderacion": "🛡️", "Niveles": "📊",
            "Diversion": "🎲", "Configuracion": "⚙️", "Developer": "💻",
            "Cumpleaños": "🎂", "Roles": "🎭", "Voice": "🎙️", 
            "Perfil": "👤", "Status": "🟢", "Backup": "💾"
        }

        for name, cog in bot.cogs.items():
            cmds = cog.get_commands()
            if not cmds: continue
            if not any(not c.hidden for c in cmds): continue

            desc_key = f"help_desc_{name.lower()}"
            description = lang_service.get_text(desc_key, lang)
            if description == desc_key: description = f"Comandos de {name}."

            options.append(discord.SelectOption(
                label=name,
                description=description[:100],
                value=name,
                emoji=emoji_map.get(name, "📂")
            ))

        super().__init__(
            placeholder=lang_service.get_text("help_placeholder", lang),
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                lang_service.get_text("error_self_action", self.lang), ephemeral=True
            )

        value = self.values[0]

        if value == "home":
            embed = await General.get_home_embed(self.ctx)
            await interaction.response.edit_message(embed=embed)
        else:
            cog = self.bot.get_cog(value)
            if not cog: return
            
            title = lang_service.get_text("help_module_title", self.lang, module=value)
            module_desc = lang_service.get_text("help_module_desc", self.lang, module=value)
            
            lista_txt = ""
            for cmd in cog.get_commands():
                if cmd.hidden: continue
                
                if isinstance(cmd, (commands.HybridGroup, commands.Group)):
                    for sub in cmd.commands:
                        desc_cmd = sub.description or sub.short_doc or "..."
                        lista_txt += f"🔹 `/{cmd.name} {sub.name}` - {desc_cmd}\n"
                
                else:
                    desc_cmd = cmd.description or cmd.short_doc or "..."
                    lista_txt += f"🔹 `/{cmd.name}` - {desc_cmd}\n"

            if not lista_txt:
                lista_txt = lang_service.get_text("help_no_cmds", self.lang)

            embed = embed_service.info(title, f"{module_desc}\n\n{lista_txt}")
            await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot, ctx, lang):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot, ctx, lang))

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(name="Traducir", callback=self.traducir_mensaje)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @staticmethod
    async def get_home_embed(ctx):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        cogs_count = len(ctx.bot.cogs)
        total_cmds = len([c for c in ctx.bot.commands if not c.hidden])
        
        title = lang_service.get_text("help_title", lang)
        desc = lang_service.get_text("help_desc", lang, user=ctx.author.display_name)
        stats = lang_service.get_text("help_stats", lang, cats=cogs_count, cmds=total_cmds)
        
        cats = [f"• {name}" for name in ctx.bot.cogs.keys() if ctx.bot.get_cog(name).get_commands()]
        cats_formatted = "\n".join(cats)
        
        embed = embed_service.info(title, f"{desc}\n\n{stats}")
        embed.add_field(name=lang_service.get_text("help_categories", lang), value=f"```\n{cats_formatted}\n```", inline=False)
        
        if ctx.bot.user.avatar:
            embed.set_thumbnail(url=ctx.bot.user.avatar.url)
        return embed

    @commands.hybrid_command(name="help", description="Muestra el panel de ayuda y comandos.")
    async def help(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        embed = await self.get_home_embed(ctx)
        view = HelpView(self.bot, ctx, lang)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="ping", description="Muestra la latencia actual del bot.")
    async def ping(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        ms = round(self.bot.latency * 1000)
        
        txt = lang_service.get_text("ping_msg", lang, ms=ms)
        await ctx.reply(embed=embed_service.info("Ping", txt, lite=True))

    @commands.hybrid_command(name="calc", description="Calculadora flexible. Ej: /calc + 5 10")
    @app_commands.describe(operacion="Usa símbolos (+, -, *, /)", num1="Primer número", num2="Segundo número")
    async def calc(self, ctx: commands.Context, operacion: str, num1: float, num2: float):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        op_map = {
            "sumar": "+", "suma": "+", "add": "+", "+": "+", "mas": "+",
            "restar": "-", "resta": "-", "minus": "-", "-": "-", "menos": "-",
            "multiplicacion": "*", "multiplicar": "*", "por": "*", "*": "*", "x": "*",
            "division": "/", "dividir": "/", "div": "/", "/": "/"
        }
        
        op_symbol = op_map.get(operacion.lower())
        
        if not op_symbol:
            await ctx.reply(embed=embed_service.error("Error", "Operación no válida.\nUsa: `+`, `-`, `*`, `/`", lite=True), ephemeral=True)
            return
        
        try:
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
            logger.warning(f"Error Calc ({ctx.author}): {e}")
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
            logger.error(f"Error Traductor: {e}")
            await interaction.followup.send(embed=embed_service.error("Error", str(e), lite=True), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))