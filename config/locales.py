# config/locales.py

LOCALES = {
    "es": {
        # --- ERRORES GLOBALES ---
        "error_title": "Error",
        "error_generic": "Ocurrió un error inesperado.",
        "error_no_perms": "No tienes permisos suficientes.",
        "error_bot_no_perms": "No tengo permisos suficientes.",
        "error_hierarchy": "No puedo realizar esta acción por jerarquía de roles.",
        "error_self_action": "No puedes usar este comando sobre ti mismo.",
        "error_missing_args": "Faltan argumentos.",
        "error_cooldown": "Estás yendo muy rápido. Espera {seconds}s.",
        
        # --- GENERAL ---
        "ping_msg": "🏓 Pong! Latencia: **{ms}ms**",
        "calc_result": "Resultado: `{a}` {op} `{b}` = **{res}**",
        "calc_error": "Error matemático: {error}",
        "trans_title": "Traducción",
        "trans_result": "**Original:** {orig}\n**Traducido:** {trans}",
        
        # --- MODERACIÓN ---
        "clear_success": "Limpieza Completada",
        "clear_desc": "Se han eliminado **{count}** mensajes.",
        "kick_title": "Usuario Expulsado",
        "kick_desc": "**{user}** ha sido expulsado.\n📝 Razón: {reason}",
        "ban_title": "Usuario Baneado",
        "ban_desc": "**{user}** ha sido baneado.\n📝 Razón: {reason}",
        
        # --- DIVERSIÓN ---
        "coinflip_title": "¡Moneda Lanzada!",
        "coinflip_desc": "La moneda ha caído en: **{result}**",
        "jumbo_title": "Emoji: {name}",
        "jumbo_error": "Solo funciona con emojis personalizados.",
        "choice_title": "He tomado una decisión",
        "choice_desc": "Entre **{a}** y **{b}**, elijo:\n\n👉 **{result}**",
        "confess_title": "🤫 Nueva Confesión",
        "confess_sent": "Tu secreto ha sido publicado en {channel}.",
        "chaos_bang": "¡Pum! **{user}** ha tenido mala suerte ({prob}%).\nCastigo: 1 minuto fuera.",

        # --- NIVELES & PERFIL ---
        "rank_title": "Rango de {user}",
        "level_up_default": "🎉 ¡Felicidades {user}! Has subido al **Nivel {level}** 🆙",
        "profile_title": "Tarjeta de {user}",
        "profile_desc": "Sin descripción.",
        "profile_stats": "--- Estadísticas ---",
        
        # --- CONFIGURACIÓN ---
        "setup_success": "Configuración Actualizada",
        "setup_desc": "✅ {type} configurado correctamente: {value}",
        "setup_chaos_desc": "{status}\n🔫 Probabilidad: **{prob}%**",
        "lang_success": "Idioma cambiado a **Español** 🇪🇸",
        
        # --- CUMPLEAÑOS ---
        "bday_title": "🎉 ¡Feliz Cumpleaños! 🎂",
        "bday_saved": "¡Fecha guardada! **{date}**",
        "bday_removed": "Tu cumpleaños ha sido eliminado.",
        "bday_server_default": "Hoy celebramos a:\n\n✨ {users} ✨"
    },
    
    "en": {
        # --- GLOBAL ERRORS ---
        "error_title": "Error",
        "error_generic": "An unexpected error occurred.",
        "error_no_perms": "You don't have enough permissions.",
        "error_bot_no_perms": "I don't have enough permissions.",
        "error_hierarchy": "I cannot perform this action due to role hierarchy.",
        "error_self_action": "You cannot perform this action on yourself.",
        "error_missing_args": "Missing arguments.",
        "error_cooldown": "You are going too fast. Wait {seconds}s.",
        
        # --- GENERAL ---
        "ping_msg": "🏓 Pong! Latency: **{ms}ms**",
        "calc_result": "Result: `{a}` {op} `{b}` = **{res}**",
        "calc_error": "Math error: {error}",
        "trans_title": "Translation",
        "trans_result": "**Original:** {orig}\n**Translated:** {trans}",
        
        # --- MODERATION ---
        "clear_success": "Clear Completed",
        "clear_desc": "**{count}** messages have been deleted.",
        "kick_title": "User Kicked",
        "kick_desc": "**{user}** has been kicked.\n📝 Reason: {reason}",
        "ban_title": "User Banned",
        "ban_desc": "**{user}** has been banned.\n📝 Reason: {reason}",
        
        # --- FUN ---
        "coinflip_title": "Coin Flipped!",
        "coinflip_desc": "The coin landed on: **{result}**",
        "jumbo_title": "Emoji: {name}",
        "jumbo_error": "Only works with custom emojis.",
        "choice_title": "I decided",
        "choice_desc": "Between **{a}** and **{b}**, I choose:\n\n👉 **{result}**",
        "confess_title": "🤫 New Confession",
        "confess_sent": "Your secret has been published in {channel}.",
        "chaos_bang": "Bang! **{user}** ran out of luck ({prob}%).\nPunishment: 1 minute timeout.",

        # --- LEVELS & PROFILE ---
        "rank_title": "{user}'s Rank",
        "level_up_default": "🎉 Congrats {user}! You reached **Level {level}** 🆙",
        "profile_title": "{user}'s Card",
        "profile_desc": "No description.",
        "profile_stats": "--- Stats ---",
        
        # --- CONFIGURATION ---
        "setup_success": "Configuration Updated",
        "setup_desc": "✅ {type} successfully set to: {value}",
        "setup_chaos_desc": "{status}\n🔫 Probability: **{prob}%**",
        "lang_success": "Language changed to **English** 🇺🇸",
        
        # --- BIRTHDAY ---
        "bday_title": "🎉 Happy Birthday! 🎂",
        "bday_saved": "Date saved! **{date}**",
        "bday_removed": "Your birthday has been removed.",
        "bday_server_default": "Today we celebrate:\n\n✨ {users} ✨"
    }
}