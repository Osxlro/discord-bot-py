import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal # <--- ESTO FALTABA
from services import embed_service

class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- LISTENER DE INTERACCIONES ---
    # Este evento escuchará CUALQUIER botón en el servidor.
    # Si el botón tiene un ID que empieza por "role:", ejecutará la lógica.
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # Solo nos interesan las interacciones con componentes (botones/menús)
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")
        
        # Verificamos si es un botón de nuestro sistema de roles
        if custom_id.startswith("role:"):
            # Formato esperado: "role:123456789"
            try:
                role_id = int(custom_id.split(":")[1])
                role = interaction.guild.get_role(role_id)
                
                if not role:
                    await interaction.response.send_message("❌ El rol asociado a este botón ya no existe en el servidor.", ephemeral=True)
                    return

                # Toggle: Si ya tiene el rol, se lo quitamos. Si no, se lo damos.
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role, reason="Botón de Auto-Rol: Quitar")
                    await interaction.response.send_message(f"❌ Te he quitado el rol **{role.name}**.", ephemeral=True)
                else:
                    await interaction.user.add_roles(role, reason="Botón de Auto-Rol: Dar")
                    await interaction.response.send_message(f"✅ Te he dado el rol **{role.name}**.", ephemeral=True)
            
            except discord.Forbidden:
                await interaction.response.send_message("⛔ No tengo permisos suficientes para gestionar este rol (Jerarquía o Permisos).", ephemeral=True)
            except Exception as e:
                # Capturamos cualquier otro error inesperado
                await interaction.response.send_message(f"Ocurrió un error: {e}", ephemeral=True)

    # --- COMANDO PARA CREAR EL BOTÓN ---
    @commands.hybrid_command(name="botonrol", description="Crea un botón para que los usuarios obtengan un rol")
    @app_commands.describe(
        rol="El rol que se entregará al pulsar el botón",
        titulo="Título del mensaje (Embed)",
        descripcion="Texto del mensaje (Embed)",
        emoji="Emoji visual para el botón (ej: 🎮)",
        color_boton="Color del botón (blue, green, red, grey)"
    )
    @commands.has_permissions(administrator=True)
    async def create_role_button(
        self, 
        ctx: commands.Context, 
        rol: discord.Role, 
        titulo: str = "Consigue tu Rol", 
        descripcion: str = "Pulsa el botón de abajo para obtener el rol.", 
        emoji: str = "✨",
        color_boton: Literal["blue", "green", "red", "grey"] = "green"
    ):
        # 1. Validaciones de Jerarquía
        if rol.position >= ctx.guild.me.top_role.position:
            embed = embed_service.error("Error de Jerarquía", "Ese rol es superior o igual a mi rol más alto. No podré entregarlo.")
            await ctx.reply(embed=embed, ephemeral=True)
            return

        # 2. Crear el Embed
        embed = embed_service.info(titulo, descripcion)
        embed.set_footer(text=f"ID del Rol: {rol.id}")

        # 3. Mapeo de colores para el botón
        styles = {
            "blue": discord.ButtonStyle.primary,
            "green": discord.ButtonStyle.success,
            "red": discord.ButtonStyle.danger,
            "grey": discord.ButtonStyle.secondary
        }

        # 4. Crear la Vista y el Botón
        # timeout=None es IMPORTANTE para que el botón no deje de funcionar visualmente,
        # aunque la lógica real la maneja el listener on_interaction.
        view = discord.ui.View(timeout=None) 
        
        button = discord.ui.Button(
            style=styles.get(color_boton, discord.ButtonStyle.success),
            label=rol.name,
            emoji=emoji,
            custom_id=f"role:{rol.id}" # <--- Esta ID es lo que lee el listener
        )
        view.add_item(button)

        # 5. Enviar mensaje
        await ctx.channel.send(embed=embed, view=view)
        await ctx.reply("✅ Botón de rol creado exitosamente.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))