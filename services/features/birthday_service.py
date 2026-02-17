import datetime
import discord
import logging
from services.core import db_service, lang_service
from ui import birthday_ui

logger = logging.getLogger(__name__)

# Re-exportar para compatibilidad con tareas y otros módulos
get_upcoming_birthdays_embed = birthday_ui.get_upcoming_birthdays_embed

async def process_daily_birthdays(bot):
    """Revisa y notifica los cumpleaños del día en todos los servidores."""
    hoy = datetime.date.today()
    fecha_str = f"{hoy.day}/{hoy.month}"
    
    users = await db_service.fetch_all(
        "SELECT user_id, personal_birthday_msg FROM users WHERE birthday = ? AND celebrate = 1", 
        (fecha_str,)
    )
    if not users: return

    for guild in bot.guilds:
        await notify_guild_birthdays(guild, users)

async def notify_guild_birthdays(guild: discord.Guild, users_rows: list):
    """Envía las felicitaciones a un servidor específico."""
    lang = await lang_service.get_guild_lang(guild.id)
    config = await db_service.get_guild_config(guild.id)
    
    channel_id = config.get('birthday_channel_id')
    if not channel_id: return
    
    channel = guild.get_channel(channel_id)
    if not channel: return

    genericos = []
    for row in users_rows:
        member = guild.get_member(row['user_id'])
        if not member: continue

        if row['personal_birthday_msg']:
            embed = birthday_ui.get_personal_birthday_embed(lang, member, row['personal_birthday_msg'])
            await channel.send(content=member.mention, embed=embed)
        else:
            genericos.append(member.mention)

    if genericos:
        embed = birthday_ui.get_server_birthday_embed(lang, genericos, config.get('server_birthday_msg'))
        await channel.send(embed=embed)

async def handle_establish_birthday(user_id: int, dia: int, mes: int, lang: str):
    """Lógica para establecer un cumpleaños."""
    try:
        datetime.date(2000, mes, dia)
        fecha = f"{dia}/{mes}"
        await db_service.execute(
            "INSERT INTO users (user_id, birthday, celebrate) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id) DO UPDATE SET birthday = excluded.birthday, celebrate = 1",
            (user_id, fecha)
        )
        return birthday_ui.get_birthday_saved_embed(lang, fecha), None
    except ValueError:
        return None, lang_service.get_text("bday_invalid", lang)

async def handle_delete_birthday(target_id: int, lang: str):
    """Lógica para eliminar un cumpleaños."""
    await db_service.execute("UPDATE users SET birthday = NULL WHERE user_id = ?", (target_id,))
    return birthday_ui.get_birthday_removed_embed(lang)

async def handle_privacy_update(user_id: int, val: int, lang: str):
    """Lógica para actualizar la privacidad."""
    await db_service.execute("UPDATE users SET celebrate = ? WHERE user_id = ?", (val, user_id))
    return birthday_ui.get_birthday_privacy_embed(lang, val)

async def handle_get_upcoming_list(guild: discord.Guild, lang: str):
    """Lógica para obtener la lista de próximos cumpleaños."""
    return await birthday_ui.get_upcoming_birthdays_embed(guild, lang)