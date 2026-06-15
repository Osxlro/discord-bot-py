import aiohttp
import re
import xml.etree.ElementTree as ET
import logging
from services.core import db_service

logger = logging.getLogger(__name__)

# Namespaces para el XML de YouTube RSS
YT_NAMESPACES = {
    'atom': 'http://www.w3.org/2005/Atom',
    'yt': 'http://www.youtube.com/xml/schemas/2015'
}

async def add_stream_alert(guild_id: int, platform: str, channel_name: str, discord_channel_id: int, role_id: int = 0) -> tuple[bool, str]:
    """
    Registra una nueva alerta de stream/video para un servidor.
    Intenta verificar y resolver el ID del canal de YouTube si es necesario.
    """
    platform = platform.lower()
    if platform != "youtube":
        return False, "invalid_platform"

    # Si es YouTube, intentamos resolver el ID del canal si no empieza con UC
    resolved_id = channel_name
    if not channel_name.startswith("UC"):
        # Asegurarnos de que tenga el formato de handle si es un nombre de usuario
        handle = channel_name if channel_name.startswith("@") else f"@{channel_name}"
        logger.info(f"Intentando resolver canal de YouTube: {handle}")
        try:
            resolved_id = await resolve_youtube_channel_id(handle)
            if not resolved_id:
                return False, "youtube_channel_not_found"
        except Exception as e:
            logger.error(f"Error resolviendo canal de YouTube {handle}: {e}")
            return False, "youtube_resolver_error"

    # Verificar si ya existe
    existing = await db_service.fetch_one(
        "SELECT 1 FROM stream_alerts WHERE guild_id = ? AND platform = ? AND channel_name = ?",
        (guild_id, platform, resolved_id)
    )
    if existing:
        return False, "already_exists"

    # Insertar en base de datos
    await db_service.execute(
        "INSERT INTO stream_alerts (guild_id, platform, channel_name, discord_channel_id, role_id) VALUES (?, ?, ?, ?, ?)",
        (guild_id, platform, resolved_id, discord_channel_id, role_id)
    )
    return True, resolved_id

async def remove_stream_alert(guild_id: int, platform: str, channel_name: str) -> bool:
    """Elimina una alerta registrada en el servidor."""
    platform = platform.lower()
    
    # Intentamos borrar directamente (buscamos por channel_name o handle si es que se guardó así)
    res = await db_service.execute(
        "DELETE FROM stream_alerts WHERE guild_id = ? AND platform = ? AND (channel_name = ? OR channel_name = ?)",
        (guild_id, platform, channel_name, f"@{channel_name}")
    )
    
    # Si no se borró nada y no empieza por UC, intentamos resolver el ID y volver a intentar
    if res.rowcount == 0 and platform == "youtube" and not channel_name.startswith("UC"):
        handle = channel_name if channel_name.startswith("@") else f"@{channel_name}"
        try:
            resolved_id = await resolve_youtube_channel_id(handle)
            if resolved_id:
                res = await db_service.execute(
                    "DELETE FROM stream_alerts WHERE guild_id = ? AND platform = ? AND channel_name = ?",
                    (guild_id, platform, resolved_id)
                )
        except Exception:
            pass

    return res.rowcount > 0

async def get_stream_alerts(guild_id: int) -> list[dict]:
    """Obtiene todas las alertas configuradas para un servidor."""
    rows = await db_service.fetch_all(
        "SELECT platform, channel_name, discord_channel_id, role_id, last_status FROM stream_alerts WHERE guild_id = ?",
        (guild_id,)
    )
    return [dict(row) for row in rows]

async def get_all_stream_alerts() -> list[dict]:
    """Obtiene todas las alertas globales registradas para el background task."""
    rows = await db_service.fetch_all(
        "SELECT guild_id, platform, channel_name, discord_channel_id, role_id, last_status FROM stream_alerts"
    )
    return [dict(row) for row in rows]

async def update_stream_status(guild_id: int, platform: str, channel_name: str, status: str):
    """Actualiza el último estado/video ID notificado para evitar duplicados."""
    await db_service.execute(
        "UPDATE stream_alerts SET last_status = ?, last_check = datetime('now') WHERE guild_id = ? AND platform = ? AND channel_name = ?",
        (status, guild_id, platform.lower(), channel_name)
    )

async def resolve_youtube_channel_id(handle: str) -> str | None:
    """
    Resuelve el ID de un canal de YouTube (UC...) a partir de su handle (@username).
    """
    url = f"https://www.youtube.com/{handle}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                
                # Intentar método 1: Meta etiqueta de channelId
                match = re.search(r'<meta itemprop="channelId" content="(UC[^"]+)"', html)
                if match:
                    return match.group(1)
                
                # Intentar método 2: RSS feed link
                match = re.search(r'href="https://www.youtube.com/feeds/videos.xml\?channel_id=(UC[^"]+)"', html)
                if match:
                    return match.group(1)
                
                # Intentar método 3: JSON interno ytInitialData
                match = re.search(r'"channelId":"(UC[^"]+)"', html)
                if match:
                    return match.group(1)
        except Exception as e:
            logger.error(f"Error en resolve_youtube_channel_id para {handle}: {e}")
            
    return None

async def check_youtube_feed(channel_id: str) -> dict | None:
    """
    Consulta el feed RSS público de un canal de YouTube y devuelve el último video si existe.
    """
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return None
                xml_data = await resp.read()
                
                root = ET.fromstring(xml_data)
                entry = root.find('atom:entry', YT_NAMESPACES)
                if entry is None:
                    return None
                
                video_id = entry.find('yt:videoId', YT_NAMESPACES).text
                title = entry.find('atom:title', YT_NAMESPACES).text
                author = entry.find('atom:author/atom:name', YT_NAMESPACES).text
                link = entry.find('atom:link', YT_NAMESPACES).attrib.get('href')
                
                return {
                    "video_id": video_id,
                    "title": title,
                    "author": author,
                    "link": link
                }
        except Exception as e:
            logger.error(f"Error consultando feed RSS de YouTube para {channel_id}: {e}")
            
    return None
