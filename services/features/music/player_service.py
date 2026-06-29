import logging
import asyncio
import discord
import wavelink
from config import settings
from services.core import lang_service, persistence_service
from services.utils import embed_service
from services.features import voice_chill_service
from services.features.music import queue_service

logger = logging.getLogger(__name__)

_next_connection_node = None
_connect_lock = asyncio.Lock()

class BotPlayer(wavelink.Player):
    def __init__(self, client=None, channel=None):
        global _next_connection_node
        nodes = [_next_connection_node] if _next_connection_node else None
        super().__init__(client, channel, nodes=nodes)
        
        _next_connection_node = None  # Resetear después de asignar
        self.home = None
        self.last_msg = None
        self.last_view = None
        self.smart_autoplay = False
        self.last_track_error = False
        self.inactive_since = None  # Inicializar explícitamente en el constructor

async def cleanup_player(player: wavelink.Player, skip_message_edit: bool = False):
    """Realiza limpieza de interfaz y persistencia al detener el player."""
    if not player: return
    guild_id = player.guild.id
    data = queue_service.get_player_data(guild_id)

    # 1. Limpiar persistencia de Voice
    voice_chill_service.voice_targets.pop(guild_id, None)

    # 2. Manejar mensaje y vista
    msg = getattr(player, "last_msg", None) or data.get("last_msg")
    view = getattr(player, "last_view", None) or data.get("last_view")
    
    if view:
        for child in view.children:
            child.disabled = True
        view.stop()

    if msg:
        try:
            if skip_message_edit:
                await msg.delete()
            else:
                await msg.edit(view=view)
        except (discord.HTTPException, discord.Forbidden): pass

    # Limpiar referencias en la caché centralizada
    data["last_msg"] = None
    data["last_view"] = None
    data["home"] = None
    data["smart_autoplay"] = False
    data["last_track_error"] = False

    # Las siguientes operaciones solo son válidas para wavelink.Player
    if isinstance(player, wavelink.Player):
        # Limpiar referencias
        player.last_msg = None
        player.last_view = None
        player.home = None # Liberar referencia al canal de texto
        
        # Limpiar cola
        if hasattr(player, "queue"):
            try: player.queue.clear()
            except Exception: pass
            
        # Resetear estados internos
        player.smart_autoplay = False
        player.last_track_error = False
        await player.set_filters(wavelink.Filters()) # Limpiar filtros

async def ensure_player(ctx, lang: str) -> wavelink.Player | None:
    """Asegura que el bot esté conectado correctamente y retorna el player."""
    logger.debug("🎵 [Music Service] Ejecutando ensure_player")

    # 0. Verificación y conexión bajo demanda si los nodos están caídos
    if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
        logger.debug("🎵 [Music Service] Nodos desconectados. Intentando reconexión...")
        await ctx.send(embed=embed_service.info(lang_service.get_text("title_info", lang), lang_service.get_text("music_connecting", lang), lite=True))
        await connect_nodes(ctx.bot)
        
        if not wavelink.Pool.nodes or not any(n.status == wavelink.NodeStatus.CONNECTED for n in wavelink.Pool.nodes.values()):
            logger.error("🎵 [Music Service] Falla crítica: No se pudo conectar a ningún nodo Lavalink.")
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_err_lavalink_nodes", lang)))
            return None

    if not ctx.author.voice:
        logger.debug("🎵 [Music Service] Usuario no está en canal de voz.")
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_join", lang)))
        return None

    channel = ctx.author.voice.channel
    permissions = channel.permissions_for(ctx.guild.me)
    if not permissions.connect or not permissions.speak:
        logger.debug("🎵 [Music Service] Permisos insuficientes para el canal de voz.")
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("voice_error_perms", lang)))
        return None

    failed_node_ids = set()
    global _next_connection_node

    for i in range(3):
        chosen_node = None
        try:
            # Ensure voice_chill_service doesn't interfere
            if ctx.guild.id in voice_chill_service.voice_targets:
                voice_chill_service.voice_targets.pop(ctx.guild.id)

            # Obtener todos los nodos conectados y filtrar los fallidos
            connected_nodes = [n for n in wavelink.Pool.nodes.values() if n.status == wavelink.NodeStatus.CONNECTED]
            available_nodes = [n for n in connected_nodes if n.identifier not in failed_node_ids]

            if not available_nodes:
                available_nodes = connected_nodes

            if available_nodes:
                # Seleccionar el nodo con menos jugadores para balancear carga
                chosen_node = min(available_nodes, key=lambda n: len(n.players))
                _next_connection_node = chosen_node
                logger.debug(f"🎵 [Music Service] Intento {i+1}/3. Nodo seleccionado para conexión: {chosen_node.identifier}")

            player: BotPlayer = ctx.voice_client

            if player and not isinstance(player, BotPlayer):
                logger.debug("🎵 [Music Service] Reemplazando VoiceClient no-BotPlayer...")
                await player.disconnect(force=True)
                await asyncio.sleep(1.0) # Shorter wait
                player = await channel.connect(cls=BotPlayer, self_deaf=True, timeout=20)
            
            elif not player:
                logger.debug(f"🎵 [Music Service] Conectando nuevo BotPlayer (intento {i+1}/3)...")
                player = await channel.connect(cls=BotPlayer, self_deaf=True, timeout=20)
            
            else: # Player is a BotPlayer
                if player.channel.id != channel.id:
                    logger.debug(f"🎵 [Music Service] Moviendo a {channel.name}...")
                    await player.move_to(channel)
                
                if not player.connected:
                    if chosen_node:
                        player._node = chosen_node  # _node es el atributo privado real (node es solo lectura)
                        logger.debug(f"🎵 [Music Service] Asignando nodo {chosen_node.identifier} al player existente.")
                    logger.debug(f"🎵 [Music Service] Reconectando player existente (intento {i+1}/3)...")
                    await player.connect(reconnect=True, self_deaf=True, timeout=20)

            if player and player.volume == 0:
                await player.set_volume(settings.LAVALINK_CONFIG.get("DEFAULT_VOLUME", 50))
            
            logger.debug("🎵 [Music Service] ensure_player completado exitosamente.")
            return player

        except (asyncio.TimeoutError, wavelink.exceptions.ChannelTimeoutException):
            # Agregar el nodo fallido a la lista de exclusión
            failed_node = None
            if ctx.voice_client:
                failed_node = ctx.voice_client._node
            if not failed_node:
                failed_node = chosen_node

            if failed_node:
                failed_node_ids.add(failed_node.identifier)
                logger.warning(f"⚠️ [Music Service] El nodo {failed_node.identifier} falló al conectar. Excluido para reintentos.")

            # Limpiar siempre la conexión zombi antes del siguiente reintento
            if ctx.voice_client:
                try:
                    await ctx.voice_client.disconnect(force=True)
                except Exception:
                    pass
                await asyncio.sleep(0.5)  # Dar tiempo al gateway para liberar el estado

            if i < 2:
                logger.warning(f"🎵 [Music Service] Timeout al conectar (intento {i+1}/3). Reintentando en 2s...")
                await asyncio.sleep(2)
            else:
                logger.error("❌ [Music Service] Timeout final al conectar.")
                err_msg = lang_service.get_text("music_error_network", lang)
                await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), err_msg))
                return None
        except Exception as e:
            logger.exception("❌ [Music Service] Error inesperado en ensure_player.")
            if ctx.voice_client:
                try: await ctx.voice_client.disconnect(force=True)
                except Exception: pass
            await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), str(e)))
            return None
    return None

async def restore_players(bot):
    """Busca sesiones guardadas y las reanuda."""
    await bot.wait_until_ready()
    # Esperar un poco a que los nodos Lavalink conecten
    await asyncio.sleep(5)
    
    records = await persistence_service.load_all("music")
    if not records:
        return

    logger.debug(f"🔄 [Music Service] Restaurando {len(records)} sesiones de música...")

    for guild_id, data in records.items():
        guild = bot.get_guild(int(guild_id))
        if not guild: continue

        v_channel = guild.get_channel(data['voice_channel_id'])
        t_channel = guild.get_channel(data['text_channel_id'])
        if not v_channel: continue

        try:
            player: BotPlayer = await v_channel.connect(cls=BotPlayer, self_deaf=True)
            await player.set_volume(data['volume'])
            player.home = t_channel
            queue_service.set_player_home(guild.id, t_channel)
            player.smart_autoplay = data.get('smart_autoplay', False)
            queue_service.get_player_data(guild.id)["smart_autoplay"] = player.smart_autoplay

            # Restaurar canción actual
            tracks = await wavelink.Playable.search(data['current_track_uri'])
            if tracks:
                current = tracks[0]
                await player.play(current, start=data['position'])

            # Restaurar cola (en segundo plano para no bloquear)
            for uri in data.get('queue_uris', []):
                t = await wavelink.Playable.search(uri)
                if t: await player.queue.put_wait(t[0])
            
            logger.debug(f"✅ Sesión restaurada en {guild.name}")
        except Exception:
            logger.exception(f"❌ Error restaurando sesión en {guild.id}")
        finally:
            await persistence_service.clear("music", guild.id)

async def connect_nodes(bot):
    """Configura y conecta a los nodos de Lavalink."""
    await bot.wait_until_ready()
    
    async with _connect_lock:
        node_configs = settings.LAVALINK_CONFIG.get("NODES", [])
        if not node_configs and "HOST" in settings.LAVALINK_CONFIG:
            node_configs = [settings.LAVALINK_CONFIG]

        if not node_configs:
            logger.error("❌ [Music Service] No se encontraron nodos de Lavalink en la configuración.")
            return

        nodes_to_connect = []
        for config in node_configs:
            identifier = config.get("IDENTIFIER", config["HOST"])
            
            # Si el nodo ya está registrado en el Pool
            if wavelink.Pool.nodes and identifier in wavelink.Pool.nodes:
                existing_node = wavelink.Pool.nodes[identifier]
                if existing_node.status == wavelink.NodeStatus.DISCONNECTED:
                    logger.info(f"🔄 Intentando reconectar nodo existente de Lavalink: {identifier}")
                    try:
                        await existing_node._connect(client=bot)
                    except Exception as e:
                        logger.error(f"❌ Error al reconectar nodo {identifier}: {e}")
                else:
                    logger.debug(f"ℹ️ El nodo {identifier} ya está registrado y en estado {existing_node.status}.")
                continue
            
            # Si no está registrado, se configura e intenta conectar
            try:
                protocol = "https" if config.get("SECURE") else "http"
                node = wavelink.Node(
                    identifier=identifier,
                    uri=f"{protocol}://{config['HOST']}:{config['PORT']}",
                    password=config['PASSWORD']
                )
                nodes_to_connect.append(node)
            except Exception as e:
                logger.error(f"❌ Error configurando nodo {identifier}: {e}")

        if not nodes_to_connect:
            return

        try:
            await wavelink.Pool.connect(nodes=nodes_to_connect, client=bot, cache_capacity=settings.LAVALINK_CONFIG.get("CACHE_CAPACITY", 100))
        except Exception as e:
            logger.exception(f"❌ Error fatal al conectar con los nodos de Lavalink: {e}")
        finally:
            # Cerrar sesiones de los nuevos nodos creados que no lograron registrarse en el pool (fugas)
            for node in nodes_to_connect:
                if node.identifier not in wavelink.Pool.nodes:
                    logger.warning(f"🧹 Cerrando sesión del nodo fallido: {node.identifier}")
                    try:
                        await node._pool_closer()
                    except Exception as cleanup_err:
                        logger.error(f"Error cerrando sesión del nodo {node.identifier}: {cleanup_err}")

async def check_voice(ctx) -> bool:
    """Verifica si el usuario puede ejecutar comandos de control."""
    lang = await lang_service.get_guild_lang(ctx.guild.id)
    player = ctx.voice_client
    
    if not player or not player.connected:
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_error_nothing", lang), lite=True), ephemeral=True)
        return False
        
    if not ctx.author.voice or (player.channel and ctx.author.voice.channel.id != player.channel.id):
        await ctx.send(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("music_control_voice_error", lang), lite=True), ephemeral=True)
        return False
    return True
