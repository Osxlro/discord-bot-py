import discord
from discord.ext import commands
from discord import app_commands
from services import embed_service

# --- VISTA PERSISTENTE ---
class RoleButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistente

    # Este listener "mágico" escucha cualquier botón cuyo custom_id empiece por "role:"
    # No necesitamos definir los botones aquí, se definen dinámicamente en el comando.
    @discord.ui.button(label="Este botón es dummy, no se verá", style=discord.ButtonStyle.primary, custom_id="persistent_view:dummy_role", row=4)
    async def dummy(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass
    
    # Sobreescribimos remove_item para quitar el dummy antes de usar la vista, 
    # o simplemente usamos dynamic_items si usamos discord.py 2.0+ avanzado, 
    # pero para mantenerlo simple y funcional con tu versión, usaremos el evento `interaction_check` global o un custom listener.
    
    # MEJOR ENFOQUE: Usar un listener global en el Cog para capturar interacciones de componentes dinámicos.
    pass

class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Registramos una vista vacía para que el bot escuche interacciones persistentes
        # Aunque en realidad, para botones dinámicos (custom_id variables), lo mejor es manejarlo en on_interaction
        pass

    # --- LISTENER DE INTERACCIONES ---
    # Esto manejará CUALQUIER botón que empiece con "role:"
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id.startswith("role:"):
            # Formato esperado: "role:123456789"
            try:
                role_id = int(custom_id.split(":")[1])
                role = interaction.guild.get_role(role_id)
                
                if not role:
                    await interaction.response.send_message("❌ El rol asociado a este botón ya no existe.", ephemeral=True)
                    return

                # Toggle: Si lo tiene, se lo quita. Si no, se lo da.
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role, reason="Self-Role Button")
                    await interaction.response.send_message(f"❌ Te he quitado el rol **{role.name}**.", ephemeral=True)
                else:
                    await interaction.user.add_roles(role, reason="Self-Role Button")
                    await interaction.response.send_message(f"✅ Te he dado el rol **{role.name}**.", ephemeral=True)
            
            except discord.Forbidden:
                await interaction.response.send_message("⛔ No tengo permisos para gestionar este rol (Jerarquía).", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    # --- COMANDO PARA CREAR EL BOTÓN ---
    @commands.hybrid_command(name="botonrol", description="Crea un botón para que los usuarios obtengan un rol")
    @app_commands.describe(
        rol="El rol que se entregará",
        titulo="Título del mensaje",
        descripcion="Texto del mensaje",
        emoji="Emoji para el botón (opcional)",
        color_boton="Color del botón (blue, green, red, grey)"
    )
    @commands.has_permissions(administrator=True)
    async def create_role_button(
        self, 
        ctx: commands.Context, 
        rol: discord.Role, 
        titulo: str = "Consigue tu Rol", 
        descripcion: str = "Pulsa el botón para obtener el rol.", 
        emoji: str = "✨",
        color_boton: Literal["blue", "green", "red", "grey"] = "green"
    ):
        # Validaciones
        if rol.position >= ctx.guild.me.top_role.position:
            await ctx.reply(embed=embed_service.error("Error", "Ese rol es superior al mío, no podré entregarlo."), ephemeral=True)
            return

        embed = embed_service.info(titulo, descripcion)
        embed.set_footer(text=f"Rol ID: {rol.id}")

        # Mapeo de colores
        styles = {
            "blue": discord.ButtonStyle.primary,
            "green": discord.ButtonStyle.success,
            "red": discord.ButtonStyle.danger,
            "grey": discord.ButtonStyle.secondary
        }

        # Creamos la vista y el botón manualmente
        view = discord.ui.View(timeout=None) # Timeout None es vital
        button = discord.ui.Button(
            style=styles.get(color_boton, discord.ButtonStyle.success),
            label=rol.name,
            emoji=emoji,
            custom_id=f"role:{rol.id}" # <--- AQUÍ ESTÁ LA MAGIA
        )
        view.add_item(button)

        await ctx.channel.send(embed=embed, view=view)
        await ctx.reply("✅ Botón de rol creado exitosamente.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))