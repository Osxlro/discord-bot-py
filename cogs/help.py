import discord
from discord import app_commands
from discord.ext import commands
from services import embed_service

class Ayuda(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'✅ Módulo Ayuda cargado.')

    @app_commands.command(name="help", description="Muestra todos los comandos y módulos disponibles")
    async def help(self, interaction: discord.Interaction):
        # 1. Crear el Embed base usando tu servicio de diseño
        embed = embed_service.info(
            title="Panel de Ayuda", 
            description="Aquí tienes la lista de todos mis sistemas activos:"
        )

        # 2. Magia: Recorrer todos los Cogs cargados en el bot
        # self.bot.cogs devuelve un diccionario {'General': <CogObject>, 'Matematicas': ...}
        for nombre_cog, cog in self.bot.cogs.items():
            
            # Obtenemos los comandos Slash definidos dentro de ese Cog
            comandos_slash = cog.get_app_commands()
            
            # Si el módulo tiene comandos, lo agregamos a la lista
            if comandos_slash:
                # Generamos una lista de texto tipo: "/comando: descripción"
                lista_txt = ""
                for cmd in comandos_slash:
                    lista_txt += f"**/ {cmd.name}** - {cmd.description}\n"
                
                # Añadimos un campo al Embed por cada Módulo
                # Usamos emojis decorativos según el nombre (opcional)
                emoji = "📂"
                if nombre_cog == "Matematicas": emoji = "🧮"
                elif nombre_cog == "General": emoji = "👋"
                
                embed.add_field(
                    name=f"{emoji} Módulo {nombre_cog}", 
                    value=lista_txt, 
                    inline=False # Para que ocupe todo el ancho
                )

        # 3. Enviar respuesta (Ephemeral=True para que solo lo vea quien lo pidió, opcional)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ayuda(bot))