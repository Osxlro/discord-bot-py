import discord
from discord.ext import commands
from services import db_service

class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return # Ignoramos bots

        # 1. Buscar configuración
        row = await db_service.fetch_one("SELECT autorole_id FROM guild_config WHERE guild_id = ?", (member.guild.id,))
        
        if not row or not row['autorole_id']:
            return

        # 2. Obtener el rol
        role_id = row['autorole_id']
        role = member.guild.get_role(role_id)

        if role:
            try:
                # 3. Dar el rol
                await member.add_roles(role, reason="Auto Rol de Bienvenida")
            except discord.Forbidden:
                print(f"❌ Error AutoRol: No tengo permisos para dar el rol {role.name} en {member.guild.name}")
            except Exception as e:
                print(f"❌ Error AutoRol: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRole(bot))