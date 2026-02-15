import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import embed_service, lang_service
from config import settings

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
                    await interaction.response.send_message(
                        embed=embed_service.error(lang_service.get_text("title_error", lang), msg, lite=True), ephemeral=True
                    )
                    return

                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
                    msg = lang_service.get_text("role_removed", lang, role=role.name)
                    await interaction.response.send_message(
                        embed=embed_service.warning(lang_service.get_text("role_title_success", lang), msg, lite=True), ephemeral=True
                    )
                else:
                    await interaction.user.add_roles(role)
                    msg = lang_service.get_text("role_added", lang, role=role.name)
                    await interaction.response.send_message(
                        embed=embed_service.success(lang_service.get_text("role_title_success", lang), msg, lite=True), ephemeral=True
                    )
            
            except discord.Forbidden:
                msg = lang_service.get_text("error_bot_no_perms", lang)
                await interaction.response.send_message(
                    embed=embed_service.error(lang_service.get_text("role_title_perms", lang), msg, lite=True), ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    embed=embed_service.error(lang_service.get_text("title_error", lang), str(e), lite=True), ephemeral=True
                )

    @commands.hybrid_command(name="rolebutton", description="Crea un botón de auto-rol")
    @app_commands.describe(rol="Rol a entregar", titulo="Título Embed", descripcion="Desc Embed")
    @commands.has_permissions(administrator=True)
    async def create_role_button(self, ctx: commands.Context, rol: discord.Role, titulo: str = None, descripcion: str = None, emoji: str = None, color_boton: Literal["blue", "green", "red", "grey"] = "green"):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if rol.position >= ctx.guild.me.top_role.position:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("error_hierarchy", lang), lite=True), ephemeral=True)
            return

        titulo = titulo or lang_service.get_text("role_default_title", lang)
        descripcion = descripcion or lang_service.get_text("role_default_desc", lang)
        emoji = emoji or settings.ROLES_CONFIG["DEFAULT_EMOJI"]

        embed = embed_service.info(titulo, descripcion, footer=f"ID: {rol.id}")
        styles = {"blue": discord.ButtonStyle.primary, "green": discord.ButtonStyle.success, "red": discord.ButtonStyle.danger, "grey": discord.ButtonStyle.secondary}

        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(style=styles.get(color_boton), label=rol.name, emoji=emoji, custom_id=f"role:{rol.id}")
        view.add_item(button)

        await ctx.channel.send(embed=embed, view=view)
        # CORRECCIÓN FINAL
        await ctx.reply(embed=embed_service.success(lang_service.get_text("role_title_success", lang), lang_service.get_text("role_btn_success", lang), lite=True), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))