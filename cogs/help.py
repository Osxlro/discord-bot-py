import discord
from discord.ext import commands
from services import embed_service

# --- 1. El Menú Desplegable (La lógica de selección) ---
class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = []
        
        # Diccionario de emojis para cada módulo (Puedes personalizarlos)
        # Asegúrate de que los nombres coincidan EXACTAMENTE con tus nombres de archivo/clase
        emoji_map = {
            "Matematicas": "🧮",
            "General": "👋",
            "Moderacion": "🛡️",
            "Diversion": "🎉",
            "Developer": "🔧",
            "Status": "📡",
            "Bienvenidas": "🚪",
            "Ayuda": "ℹ️",
            "Logger": "📝"
        }

        # Recorremos dinámicamente todos los Cogs cargados
        for nombre_cog, cog in bot.cogs.items():
            # Obtenemos los comandos y filtramos los ocultos
            cmds = [c for c in cog.get_commands() if not c.hidden]
            
            # Si el módulo no tiene comandos públicos, no lo mostramos en la lista
            if not cmds:
                continue
            
            # Buscamos el emoji, si no existe usamos una carpeta genérica
            emoji = emoji_map.get(nombre_cog, "📂")
            
            options.append(discord.SelectOption(
                label=nombre_cog,
                description=f"Ver {len(cmds)} comandos de {nombre_cog}",
                emoji=emoji,
                value=nombre_cog
            ))

        # Configuración del menú
        super().__init__(
            placeholder="Selecciona una categoría...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    # Esto se ejecuta cuando el usuario selecciona algo
    async def callback(self, interaction: discord.Interaction):
        # 1. Identificar qué módulo eligió
        nombre_cog = self.values[0]
        cog = self.bot.get_cog(nombre_cog)
        
        # 2. Construir el embed nuevo con los comandos de ESE módulo
        embed = embed_service.info(
            title=f"Módulo {nombre_cog}", 
            description=f"Aquí tienes los comandos disponibles en **{nombre_cog}**:"
        )
        
        cmds = [c for c in cog.get_commands() if not c.hidden]
        lista_txt = ""
        
        for cmd in cmds:
            # Obtener descripción, si no tiene ponemos un texto default
            desc = cmd.description or cmd.help or "Sin descripción"
            
            # Mostramos el formato /comando
            lista_txt += f"🔹 **/{cmd.name}** - {desc}\n"
            
        embed.add_field(name="Comandos", value=lista_txt or "No hay comandos disponibles.")
        
        # 3. Editar el mensaje original con el nuevo contenido
        await interaction.response.edit_message(embed=embed)

# --- 2. La Vista (Contiene el menú y botones) ---
class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=180) # El menú deja de funcionar a los 3 min para ahorrar memoria
        
        # Añadimos el menú desplegable que creamos arriba
        self.add_item(HelpSelect(bot))
        
        # (Opcional) Añadimos un botón de enlace como en la foto
        self.add_item(discord.ui.Button(
            label="Sitio Web / Soporte", 
            url="https://google.com", 
            style=discord.ButtonStyle.link,
            emoji="🔗"
        ))

# --- 3. El Comando /help ---
class Ayuda(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Muestra el menú de ayuda interactivo")
    async def help(self, ctx: commands.Context):
        # 1. Embed "Portada" (Lo primero que se ve)
        conteo_comandos = len([c for c in self.bot.commands if not c.hidden])
        conteo_categorias = len(self.bot.cogs)

        embed = embed_service.info(
            title="Panel de Ayuda", 
            description=f"Hola **{ctx.author.name}**, soy **{self.bot.user.name}**.\nUsa el menú desplegable de abajo para explorar mis funciones."
        )
        
        # Mostramos estadísticas bonitas tipo Nekotina
        embed.add_field(name="📊 Estadísticas", value=f"• **{conteo_categorias}** Categorías\n• **{conteo_comandos}** Comandos", inline=False)

        # Generamos una "Grilla" de texto con las categorías disponibles
        nombres_cogs = [name for name in self.bot.cogs.keys() if self.bot.get_cog(name).get_commands()]
        lista_visual = "```\n" + "\n".join(nombres_cogs) + "\n```"
        
        embed.add_field(name="📂 Categorías Disponibles", value=lista_visual, inline=False)
        
        # 2. Crear la vista interactiva
        view = HelpView(self.bot)
        
        # 3. Enviar mensaje
        await ctx.reply(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ayuda(bot))