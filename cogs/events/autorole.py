import discord
from discord.ext import commands
from services import db_service, lang_service

class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return # Ignoramos bots

        # 1. Buscar configuración
        config = await db_service.get_guild_config(member.guild.id)
        role_id = config.get('autorole_id')
        
        if not role_id:
            return

        # 2. Obtener el rol
        role = member.guild.get_role(role_id)

        if role:
            try:
                # 3. Dar el rol
                lang = await lang_service.get_guild_lang(member.guild.id)
                await member.add_roles(role, reason=lang_service.get_text("autorole_reason", lang))
            except discord.Forbidden:
                print(f"❌ Error AutoRol: No tengo permisos para dar el rol {role.name} en {member.guild.name}")
            except Exception as e:
                print(f"❌ Error AutoRol: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRole(bot))