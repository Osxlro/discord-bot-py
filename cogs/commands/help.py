import discord
from discord.ext import commands
from services import embed_service, lang_service

class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, lang: str):
        self.bot = bot
        self.lang = lang
        
        options = [discord.SelectOption(label=lang_service.get_text("help_home", lang), description=lang_service.get_text("help_home_desc", lang), emoji="🏠", value="inicio")]

        # Mapa de emojis
        emoji_map = {
            "General": "🌐", "Moderacion": "🔨", "Diversion": "🎲", "Developer": "💻", 
            "Status": "🟢", "Bienvenidas": "👋", "Ayuda": "❓", "Logger": "📜", 
            "Niveles": "⭐", "Roles": "🎭", "Configuracion": "⚙️", "Backup": "💾", 
            "Perfil": "👤"
        }

        for name, cog in bot.cogs.items():
            if not cog.get_commands(): continue
            options.append(discord.SelectOption(label=name, emoji=emoji_map.get(name, "📂"), value=name))

        super().__init__(placeholder=lang_service.get_text("help_placeholder", lang), min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "inicio":
            await interaction.response.edit_message(embed=self.view.main_embed)
            return

        name = self.values[0]
        cog = self.bot.get_cog(name)
        
        title = lang_service.get_text("help_module_title", self.lang, module=name)
        desc = lang_service.get_text("help_module_desc", self.lang, module=name)
        embed = embed_service.info(title, desc)
        
        lista_txt = ""
        # Mostramos también la descripción de los comandos
        for cmd in cog.get_commands():
            if cmd.hidden: continue
            
            if isinstance(cmd, commands.HybridGroup):
                for sub in cmd.commands:
                    desc_cmd = sub.description or "..."
                    lista_txt += f"🔹 `/{cmd.name} {sub.name}` - {desc_cmd}\n"
            else:
                desc_cmd = cmd.description or "..."
                lista_txt += f"🔹 `/{cmd.name}` - {desc_cmd}\n"
            
        embed.add_field(name="Comandos", value=lista_txt or lang_service.get_text("help_no_cmds", self.lang))
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, main_embed: discord.Embed, lang: str):
        super().__init__(timeout=180)
        self.main_embed = main_embed
        self.add_item(HelpSelect(bot, lang))

class Ayuda(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Muestra el menú de ayuda")
    async def help(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        conteo_comandos = len([c for c in self.bot.commands if not c.hidden])
        conteo_categorias = len(self.bot.cogs)

        title = lang_service.get_text("help_title", lang)
        desc = lang_service.get_text("help_desc", lang, user=ctx.author.name)
        embed = embed_service.info(title, desc, thumbnail=self.bot.user.display_avatar.url)
        
        stats_txt = lang_service.get_text("help_stats", lang, cats=conteo_categorias, cmds=conteo_comandos)
        embed.add_field(name="Stats", value=stats_txt, inline=False)

        cat_title = lang_service.get_text("help_categories", lang)
        cats = [name for name in self.bot.cogs.keys() if self.bot.get_cog(name).get_commands()]
        
        # AQUÍ ESTÁ EL ARREGLO VISUAL: Saltos de línea
        cats_formatted = "\n".join([f"• {c}" for c in cats])
        embed.add_field(name=cat_title, value=f"```\n{cats_formatted}\n```", inline=False)
        
        view = HelpView(self.bot, embed, lang)
        await ctx.reply(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ayuda(bot))