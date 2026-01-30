import discord
from discord.ext import commands
from services import lang_service, embed_service

class HelpSelect(discord.ui.Select):
    def __init__(self, bot, ctx, lang):
        self.bot = bot
        self.ctx = ctx
        self.lang = lang
        
        # Opción de Inicio
        options = [
            discord.SelectOption(
                label=lang_service.get_text("help_home", lang),
                description=lang_service.get_text("help_home_desc", lang),
                value="home",
                emoji="🏠"
            )
        ]

        # Mapa de emojis estáticos para decorar
        emoji_map = {
            "General": "💡", "Moderacion": "🛡️", "Niveles": "📊",
            "Diversion": "🎲", "Configuracion": "⚙️", "Developer": "💻",
            "Cumpleaños": "🎂", "Roles": "🎭", "Voice": "🎙️", 
            "Perfil": "👤", "Status": "🟢", "Backup": "💾"
        }

        # Generar opciones dinámicamente basado en los Cogs cargados
        for name, cog in bot.cogs.items():
            cmds = cog.get_commands()
            if not cmds: continue
            if not any(not c.hidden for c in cmds): continue

            # Descripción de la CATEGORÍA (Desde locales.py)
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
            embed = await HelpCog.get_home_embed(self.ctx)
            await interaction.response.edit_message(embed=embed)
        else:
            cog = self.bot.get_cog(value)
            if not cog: return
            
            # Título y descripción del módulo
            title = lang_service.get_text("help_module_title", self.lang, module=value)
            module_desc = lang_service.get_text("help_module_desc", self.lang, module=value)
            
            # --- AQUÍ ESTÁ LA MAGIA AUTOMÁTICA ---
            lista_txt = ""
            for cmd in cog.get_commands():
                if cmd.hidden: continue
                
                # Caso: Es un Grupo (ej: /status)
                if isinstance(cmd, (commands.HybridGroup, commands.Group)):
                    for sub in cmd.commands:
                        # Lee la descripción del CÓDIGO (sub.description)
                        desc_cmd = sub.description or sub.short_doc or "..."
                        lista_txt += f"🔹 `/{cmd.name} {sub.name}` - {desc_cmd}\n"
                
                # Caso: Comando normal
                else:
                    # Lee la descripción del CÓDIGO (cmd.description)
                    desc_cmd = cmd.description or cmd.short_doc or "..."
                    lista_txt += f"🔹 `/{cmd.name}` - {desc_cmd}\n"

            # Si no hay comandos (por alguna razón)
            if not lista_txt:
                lista_txt = lang_service.get_text("help_no_cmds", self.lang)

            embed = embed_service.info(title, f"{module_desc}\n\n{lista_txt}")
            await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot, ctx, lang):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot, ctx, lang))

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def get_home_embed(ctx):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        cogs_count = len(ctx.bot.cogs)
        total_cmds = len([c for c in ctx.bot.commands if not c.hidden])
        
        title = lang_service.get_text("help_title", lang)
        desc = lang_service.get_text("help_desc", lang, user=ctx.author.display_name)
        stats = lang_service.get_text("help_stats", lang, cats=cogs_count, cmds=total_cmds)
        
        # Lista de categorías bonita
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

async def setup(bot):
    await bot.add_cog(HelpCog(bot))