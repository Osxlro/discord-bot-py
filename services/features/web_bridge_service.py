import datetime
import discord
from discord.ext import commands
from typing import Dict, List, Any
from services.repositories.user_repository import UserRepository

def get_bot_status(bot: commands.Bot) -> Dict[str, Any]:
    """Obtiene estadísticas de rendimiento y estado del bot en tiempo real."""
    latency = round(bot.latency * 1000, 2) if bot.latency else 0.0
    
    # Calcular Uptime
    uptime_sec = 0.0
    start_time = getattr(bot, "start_time", None)
    if start_time:
        delta = datetime.datetime.now(datetime.timezone.utc) - start_time
        uptime_sec = delta.total_seconds()
        
    # Formatear Uptime de forma legible (ej: 2d 5h 12m)
    days = int(uptime_sec // 86400)
    hours = int((uptime_sec % 86400) // 3600)
    minutes = int((uptime_sec % 3600) // 60)
    
    uptime_str = ""
    if days > 0:
        uptime_str += f"{days}d "
    if hours > 0 or days > 0:
        uptime_str += f"{hours}h "
    uptime_str += f"{minutes}m"
    if not uptime_str:
        uptime_str = "0m"
    
    guilds_count = len(bot.guilds)
    users_count = sum(guild.member_count for guild in bot.guilds if guild.member_count)
    commands_count = len(bot.commands) + len(bot.tree.get_commands())
    
    return {
        "latency": latency,
        "uptime_seconds": uptime_sec,
        "uptime_str": uptime_str.strip(),
        "guilds_count": guilds_count,
        "users_count": users_count,
        "commands_count": commands_count
    }

def get_commands_by_category(bot: commands.Bot) -> Dict[str, List[Dict[str, Any]]]:
    """Agrupa y estructura todos los comandos registrados en el bot por categorías."""
    categories: Dict[str, List[Dict[str, Any]]] = {}
    
    # 1. Comandos tradicionales / híbridos cargados en Cogs
    for cog_name, cog in bot.cogs.items():
        # Saltarse cogs de utilidad internos o no públicos
        if cog_name.lower() in ["developer", "healthcheck", "optimizador", "optimization", "backup"]:
            continue
            
        cog_commands = cog.get_commands()
        if not cog_commands:
            continue
            
        cmd_list = []
        for cmd in cog_commands:
            if cmd.hidden:
                continue
            cmd_list.append({
                "name": cmd.name,
                "description": cmd.description or "Sin descripción.",
                "type": "Híbrido" if isinstance(cmd, commands.HybridCommand) else "Prefijo"
            })
            
        if cmd_list:
            categories[cog_name] = cmd_list
            
    # 2. Comandos Slash globales registrados únicamente en el CommandTree
    tree_commands = bot.tree.get_commands()
    if tree_commands:
        slash_list = []
        for cmd in tree_commands:
            # Los ContextMenu no son comandos Slash de escribir y no tienen descripción, los ignoramos
            if isinstance(cmd, discord.app_commands.ContextMenu):
                continue
                
            # Evitar duplicar si ya está listado en Cogs
            already_listed = False
            for cat_list in categories.values():
                if any(c["name"] == cmd.name for c in cat_list):
                    already_listed = True
                    break
            if already_listed:
                continue
                
            slash_list.append({
                "name": cmd.name,
                "description": getattr(cmd, "description", "Sin descripción.") or "Sin descripción.",
                "type": "Slash"
            })
            
        if slash_list:
            categories["Slash Globales"] = slash_list
            
    return categories

async def get_user_dashboard_data(user_id: int) -> Dict[str, Any]:
    """Obtiene los datos estructurados del perfil global y economía de un usuario."""
    user_data = await UserRepository.get_user_data(user_id)
    if not user_data:
        return {
            "user_id": user_id,
            "coins": 0,
            "birthday": None,
            "description": "Sin descripción.",
            "celebrate": 1
        }
        
    return {
        "user_id": user_id,
        "coins": user_data.get("coins", 0),
        "birthday": user_data.get("birthday"),
        "description": user_data.get("description", "Sin descripción."),
        "celebrate": user_data.get("celebrate", 1)
    }
