import datetime
import discord
from services.utils import embed_service
from config import settings
from services.core import db_service, lang_service

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

def get_personal_birthday_embed(lang: str, member: discord.Member, personal_msg: str) -> discord.Embed:
    """Genera el embed para una felicitación personalizada."""
    title = lang_service.get_text("bday_title", lang)
    msg = personal_msg.replace("{user}", member.mention)
    return embed_service.success(title, msg, thumbnail=member.display_avatar.url)

def get_server_birthday_embed(lang: str, mentions: list[str], server_msg: str = None) -> discord.Embed:
    """Genera el embed para la felicitación genérica del servidor."""
    title = lang_service.get_text("bday_title", lang)
    msg_base = server_msg or lang_service.get_text("bday_server_default", lang)
    
    mentions_str = ", ".join(mentions)
    msg_final = msg_base.replace("{users}", mentions_str).replace("{user}", mentions_str)
    
    return embed_service.success(title, msg_final, thumbnail=settings.BIRTHDAY_CONFIG["CAKE_ICON"])

def get_birthday_saved_embed(lang: str, date: str) -> discord.Embed:
    """Genera el embed de éxito al guardar un cumpleaños."""
    msg = lang_service.get_text("bday_saved", lang, date=date)
    return embed_service.success(lang_service.get_text("title_success", lang), msg)

def get_birthday_removed_embed(lang: str) -> discord.Embed:
    """Genera el embed de éxito al eliminar un cumpleaños."""
    return embed_service.success(lang_service.get_text("title_success", lang), lang_service.get_text("bday_removed", lang))

def get_birthday_privacy_embed(lang: str, val: int) -> discord.Embed:
    """Genera el embed de éxito al cambiar la privacidad."""
    msg = lang_service.get_text("bday_visible" if val else "bday_hidden", lang)
    return embed_service.success(lang_service.get_text("bday_privacy", lang), msg)