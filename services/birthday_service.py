import datetime
import discord
import logging
from services import db_service, lang_service, embed_service
from config import settings

logger = logging.getLogger(__name__)

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
            msg = row['personal_birthday_msg'].replace("{user}", member.mention)
            title = lang_service.get_text("bday_title", lang)
            await channel.send(
                content=member.mention, 
                embed=embed_service.success(title, msg, thumbnail=member.display_avatar.url)
            )
        else:
            genericos.append(member.mention)

    if genericos:
        msg_base = config.get('server_birthday_msg') or lang_service.get_text("bday_server_default", lang)
        # Reemplazo doble para asegurar compatibilidad con placeholders antiguos
        msg_final = msg_base.replace("{users}", ", ".join(genericos)).replace("{user}", ", ".join(genericos))
        title = lang_service.get_text("bday_title", lang)
        await channel.send(
            embed=embed_service.success(title, msg_final, thumbnail=settings.BIRTHDAY_CONFIG["CAKE_ICON"])
        )

async def get_upcoming_birthdays_embed(guild: discord.Guild, lang: str) -> discord.Embed:
    """Genera el embed con la lista de próximos cumpleaños."""
    rows = await db_service.fetch_all(
        "SELECT user_id, birthday FROM users WHERE birthday IS NOT NULL AND celebrate = 1"
    )
    
    lista = []
    hoy = datetime.date.today()
    for row in rows:
        try:
            d, m = map(int, row['birthday'].split('/'))
            bday = datetime.date(hoy.year, m, d)
            if bday < hoy: bday = datetime.date(hoy.year + 1, m, d)
            diff = (bday - hoy).days
            lista.append((diff, row['user_id'], row['birthday']))
        except Exception:
            continue
    
    lista.sort(key=lambda x: x[0])
    txt = ""
    for dias, uid, fecha in lista[:settings.BIRTHDAY_CONFIG["LIST_LIMIT"]]:
        user = guild.get_member(uid)
        if user:
            key = "bday_today" if dias == 0 else "bday_soon"
            txt += lang_service.get_text(key, lang, user=user.display_name, date=fecha, days=dias) + "\n"

    return embed_service.info(lang_service.get_text("bday_list_title", lang), txt or lang_service.get_text("bday_list_empty", lang))