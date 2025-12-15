import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import embed_service, lang_service

class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component: return
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id.startswith("role:"):
            lang = await lang_service.get_guild_lang(interaction.guild_id)
            try:
                role_id = int(custom_id.split(":")[1])
                role = interaction.guild.get_role(role_id)
                
                if not role:
                    msg = lang_service.get_text("role_not_found", lang)
                    await interaction.response.send_message(msg, ephemeral=True)
                    return

                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
                    msg = lang_service.get_text("role_removed", lang, role=role.name)
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.user.add_roles(role)
                    msg = lang_service.get_text("role_added", lang, role=role.name)
                    await interaction.response.send_message(msg, ephemeral=True)
            
            except discord.Forbidden:
                await interaction.response.send_message(lang_service.get_text("error_bot_no_perms", lang), ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    @commands.hybrid_command(name="botonrol", description="Crea un botón de auto-rol")
    @app_commands.describe(rol="Rol a entregar", titulo="Título Embed", descripcion="Desc Embed")
    @commands.has_permissions(administrator=True)
    async def create_role_button(self, ctx: commands.Context, rol: discord.Role, titulo: str = "Rol", descripcion: str = "Click para obtener rol", emoji: str = "✨", color_boton: Literal["blue", "green", "red", "grey"] = "green"):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if rol.position >= ctx.guild.me.top_role.position:
            await ctx.reply(embed=embed_service.error("Error", lang_service.get_text("error_hierarchy", lang)), ephemeral=True)
            return

        embed = embed_service.info(titulo, descripcion, footer=f"ID: {rol.id}")
        styles = {"blue": discord.ButtonStyle.primary, "green": discord.ButtonStyle.success, "red": discord.ButtonStyle.danger, "grey": discord.ButtonStyle.secondary}

        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(style=styles.get(color_boton), label=rol.name, emoji=emoji, custom_id=f"role:{rol.id}")
        view.add_item(button)

        await ctx.channel.send(embed=embed, view=view)
        await ctx.reply(lang_service.get_text("role_btn_success", lang), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))