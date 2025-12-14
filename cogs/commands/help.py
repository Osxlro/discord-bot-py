import discord
from discord.ext import commands
from services import embed_service

def contar_comandos(cog):
    contador = 0
    for cmd in cog.get_commands():
        if cmd.hidden:
            continue
        # Si es un grupo (ej: /admin), contamos sus hijos
        if isinstance(cmd, commands.HybridGroup) or isinstance(cmd, commands.Group):
            contador += len(cmd.commands)
        else:
            contador += 1
    return contador

class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Opción para volver al inicio (Portada)
        options = [
            discord.SelectOption(
                label="Inicio",
                description="Volver al panel principal",
                emoji="🏠",
                value="inicio"
            )
        ]

        # Mapa de Emojis para cada categoría
        emoji_map = {
            "General": "🌐",      # Ahora incluye matématicas
            "Moderacion": "🔨",
            "Diversion": "🎲",
            "Developer": "💻",
            "Status": "🟢",
            "Bienvenidas": "👋",
            "Ayuda": "❓",
            "Logger": "📜",
            "Niveles": "⭐",      # Nuevo icono para niveles
            "Roles": "🎭",
            "Configuracion": "⚙️",
            "Backup": "💾"
        }

        # Generamos las opciones dinámicamente según los Cogs cargados
        for name, cog in bot.cogs.items():
            cmds_count = contar_comandos(cog) # <--- USAMOS LA NUEVA FUNCIÓN
            if cmds_count == 0:
                continue
            
            emoji = emoji_map.get(name, "📂")
            
            options.append(discord.SelectOption(
                label=name,
                description=f"Ver {cmds_count} comandos", # <--- AHORA EL NÚMERO ES REAL
                emoji=emoji,
                value=name
            ))

        super().__init__(
            placeholder="Selecciona una categoría...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # Si elige "Inicio", restauramos el embed original (guardado en la View)
        if self.values[0] == "inicio":
            await interaction.response.edit_message(embed=self.view.main_embed)
            return

        # Si elige una categoría, buscamos el Cog
        nombre_cog = self.values[0]
        cog = self.bot.get_cog(nombre_cog)
        
        embed = embed_service.info(
            title=f"Módulo {nombre_cog}", 
            description=f"Comandos disponibles en **{nombre_cog}**:"
        )
        
        lista_txt = ""
        cmds = [c for c in cog.get_commands() if not c.hidden]

        for cmd in cmds:
            # Detectamos si es un GRUPO de comandos (ej: /admin ban, /admin kick)
            if isinstance(cmd, commands.HybridGroup):
                for sub in cmd.commands:
                    desc = sub.description or "Sin descripción"
                    # Mostramos: 🔹 /padre hijo - descripción
                    lista_txt += f"🔹 `/{cmd.name} {sub.name}` - {desc}\n"
            else:
                # Comando normal
                desc = cmd.description or cmd.help or "Sin descripción"
                lista_txt += f"🔹 `/{cmd.name}` - {desc}\n"
            
        embed.add_field(name="Comandos", value=lista_txt or "No hay comandos disponibles.")
        
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, main_embed: discord.Embed):
        super().__init__(timeout=180)
        # Guardamos el embed de portada para poder volver a él con el botón "Inicio"
        self.main_embed = main_embed
        
        self.add_item(HelpSelect(bot))
        
        self.add_item(discord.ui.Button(
            label="Soporte", 
            url="https://google.com", 
            style=discord.ButtonStyle.link,
            emoji="🔗"
        ))

class Ayuda(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Muestra el menú de ayuda interactivo")
    async def help(self, ctx: commands.Context):
        # 1. Estadísticas
        conteo_comandos = len([c for c in self.bot.commands if not c.hidden])
        conteo_categorias = len(self.bot.cogs)

        embed = embed_service.info(
            title="Panel de Ayuda", 
            description=f"Hola **{ctx.author.name}**. Usa el menú de abajo para explorar las funciones."
        )
        
        embed.add_field(name="📊 Estadísticas", value=f"• **{conteo_categorias}** Categorías\n• **{conteo_comandos}** Comandos", inline=False)

        # 2. Lista Visual de Categorías (Estilo Nekotina)
        # Obtenemos solo categorías con comandos visibles
        nombres_cogs = [name for name in self.bot.cogs.keys() if self.bot.get_cog(name).get_commands()]
        
        # Formato de bloque de código
        lista_visual = "```\n" + "\n".join(nombres_cogs) + "\n```"
        
        embed.add_field(name="📂 Categorías Disponibles", value=lista_visual, inline=False)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        # 3. Vista y Envío
        view = HelpView(self.bot, embed)
        await ctx.reply(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ayuda(bot))