import datetime
from discord.ext import commands
from services.features import birthday_service
from services.repositories.user_repository import UserRepository

class BirthdayEvents(commands.Cog):
    """Eventos relacionados con cumpleaños."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Felicita al usuario si se une el día de su cumpleaños."""
        hoy = datetime.date.today()
        fecha_str = f"{hoy.day}/{hoy.month}"
        
        user_data = await UserRepository.get_user_data(member.id)
        if user_data and user_data.get('birthday') == fecha_str and user_data.get('celebrate') == 1:
            await birthday_service.notify_guild_birthdays(member.guild, [user_data])

async def setup(bot: commands.Bot):
    await bot.add_cog(BirthdayEvents(bot))