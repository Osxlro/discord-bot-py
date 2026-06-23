import discord
import datetime
import logging
from config import settings
from services.core import lang_service

logger = logging.getLogger(__name__)

async def update_presence(bot: discord.Client, player, track, lang: str):
    """Actualiza el Rich Presence del bot basado en la canción actual."""
    start_time = datetime.datetime.now(datetime.timezone.utc)
    end_time = None
    if not track.is_stream:
        end_time = start_time + datetime.timedelta(milliseconds=track.length)

    single_label = lang_service.get_text("music_album_single", lang)
    album_obj = getattr(track, "album", None)
    album_name = getattr(album_obj, "name", single_label) if album_obj else single_label

    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name=f"{track.title}",
        details=f"💿 {album_name}",
        state=f"👤 {track.author} | 🔊 {player.volume}%",
        start=start_time,
        end=end_time,
        assets={
            'large_image': settings.CONFIG["bot_config"]["presence_asset"],
            'large_text': settings.CONFIG["bot_config"]["description"]
        }
    )
    await bot.change_presence(activity=activity)

async def reset_presence(bot: discord.Client):
    """Restaura el estado normal del bot al detener la música."""
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name=f"{settings.CONFIG['bot_config']['prefix']}help",
        assets={'large_image': settings.CONFIG["bot_config"]["presence_asset"]}
    )
    await bot.change_presence(activity=activity)
