import datetime
from discord.ext import commands
from services.features import birthday_service
from services.core import db_service

class BirthdayEvents(commands.Cog):
    """Eventos relacionados con cumpleaños."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Felicita al usuario si se une el día de su cumpleaños."""
        hoy = datetime.date.today()
        fecha_str = f"{hoy.day}/{hoy.month}"
        
        user_row = await db_service.fetch_one(
            "SELECT user_id, personal_birthday_msg FROM users WHERE user_id = ? AND birthday = ? AND celebrate = 1", 
            (member.id, fecha_str)
        )
        if user_row:
            await birthday_service.notify_guild_birthdays(member.guild, [user_row])

async def setup(bot: commands.Bot):
    await bot.add_cog(BirthdayEvents(bot))