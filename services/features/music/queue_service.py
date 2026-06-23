import discord
from config import settings
from services.core import lang_service
from services.utils import embed_service

_player_data = {}

def get_player_data(guild_id: int) -> dict:
    """Retorna los datos persistentes del reproductor de un servidor."""
    if guild_id not in _player_data:
        _player_data[guild_id] = {
            "home": None,
            "last_msg": None,
            "last_view": None,
            "smart_autoplay": False,
            "last_track_error": False
        }
    return _player_data[guild_id]

def set_player_home(guild_id: int, channel: discord.TextChannel):
    """Establece el canal de texto asignado para el reproductor."""
    data = get_player_data(guild_id)
    data["home"] = channel

def get_player_home(guild_id: int) -> discord.TextChannel | None:
    """Retorna el canal de texto del reproductor."""
    return get_player_data(guild_id).get("home")

def get_queue_pages(player, lang: str) -> list[discord.Embed]:
    """Genera las páginas de embeds para la cola de reproducción."""
    if not player or (not player.current and player.queue.is_empty):
        return []

    pages = []
    queue_list = list(player.queue)
    chunk_size = settings.MUSIC_CONFIG["QUEUE_PAGE_SIZE"]
    chunks = [queue_list[i:i + chunk_size] for i in range(0, len(queue_list), chunk_size)]

    if not chunks and player.current:
        chunks = [[]]

    for i, chunk in enumerate(chunks):
        desc = ""
        if player.current:
            desc += lang_service.get_text("music_queue_current", lang, title=player.current.title) + "\n\n"
        
        if chunk:
            desc += lang_service.get_text("music_queue_next", lang) + "\n"
            for j, track in enumerate(chunk):
                idx = (i * chunk_size) + j + 1
                desc += f"`{idx}.` {track.title} - *{track.author}*\n"
        
        embed = embed_service.info(
            title=lang_service.get_text("music_queue_title", lang),
            description=desc,
            footer=lang_service.get_text("music_queue_footer", lang, current=i+1, total=len(chunks), tracks=len(player.queue)),
            lite=True
        )
        pages.append(embed)
    
    return pages

async def sync_ui(player):
    """Sincroniza el estado visual de la última vista activa del reproductor."""
    view = getattr(player, "last_view", None)
    msg = getattr(player, "last_msg", None)
    if view and msg:
        view._sync_state()
        try:
            await msg.edit(view=view)
        except discord.HTTPException:
            pass
