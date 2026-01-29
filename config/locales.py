# config/locales.py

LOCALES = {
    "es": {
        # --- ERRORES GLOBALES ---
        "error_title": "Error",
        "error_generic": "❌ Ocurrió un error inesperado.",
        "error_no_perms": "❌ No tienes permisos suficientes.",
        "error_bot_no_perms": "❌ No tengo permisos suficientes.",
        "error_hierarchy": "❌ No puedo realizar esta acción por jerarquía de roles.",
        "error_self_action": "❌ No puedes usar este comando sobre ti mismo.",
        "error_missing_args": "❌ Faltan argumentos.",
        "error_cooldown": "⏳ Estás yendo muy rápido. Espera {seconds}s.",
        
        # --- GENERAL ---
        "ping_msg": "🏓 Pong! Latencia: **{ms}ms**",
        "calc_result": "Resultado: `{a}` {op} `{b}` = **{res}**",
        "calc_error": "Error matemático: {error}",
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
        "jumbo_invalid": "Eso no parece ser un emoji válido.",
        "choice_title": "He tomado una decisión",
        "choice_desc": "Entre **{a}** y **{b}**, elijo:\n\n👉 **{result}**",
        "confess_title": "🤫 Nueva Confesión",
        "confess_sent": "Tu secreto ha sido publicado en {channel}.",

        # --- NIVELES & PERFIL ---
        "rank_title": "Rango de {user}",
        "rank_no_data": "Sin datos de XP.",
        "level_up_default": "🎉 ¡Felicidades {user}! Has subido al **Nivel {level}** en {server} 🆙",
        "leaderboard_title": "🏆 Top XP: {server}",
        "leaderboard_empty": "Nadie tiene experiencia en este servidor aún.",
        "profile_title": "Tarjeta de {user}",
        "profile_desc": "Sin descripción.",
        "profile_no_bday": "No establecido",
        "profile_server_stats": "**--- Estadísticas del Servidor ---**",
        "profile_custom_msgs": "--- Mensajes Personalizados ---",
        "profile_update_success": "Perfil Actualizado",
        "profile_desc_saved": "Tu descripción ha sido guardada.",
        "profile_msg_saved": "Tu mensaje ha sido configurado.",
        
        # --- REBIRTH SYSTEM (NUEVO) ---
        "rebirth_success": "✨ **¡RENACIMIENTO COMPLETADO!** ✨\nHas sacrificado tu nivel 100+ para renacer. Ahora tienes **{rebirths}** Rebirth(s).\nTu nivel ha vuelto a 1.",
        "rebirth_fail_level": "❌ Aún no estás listo para renacer. Necesitas ser **Nivel 100** mínimo (Eres nivel {level}).",
        "rebirth_fail_generic": "❌ No se pudo completar el renacimiento.",
        "rebirth_status": "🌀 Rebirths: {count}",

        # --- SIMULACIÓN / PREVIEW (NUEVO) ---
        "simulation_title": "🔮 Simulación de Evento: {event}",
        "simulation_footer": "Este es un mensaje de prueba solo visible para ti (o en este canal).",
        "sim_welcome": "Bienvenida",
        "sim_level": "Subida de Nivel",
        "sim_birthday": "Cumpleaños",
        "sim_invalid": "❌ Evento no válido. Usa: `welcome`, `level`, `birthday`.",
        
        # --- BACKUP (NUEVO) ---
        "backup_disabled": "⚠️ El envío de backups al dueño está desactivado en settings.",
        
        # --- CUMPLEAÑOS ---
        "bday_title": "🎉 ¡Feliz Cumpleaños! 🎂",
        "bday_saved": "¡Fecha guardada! **{date}**",
        "bday_removed": "Tu cumpleaños ha sido eliminado.",
        "bday_server_default": "Hoy es un día especial. Queremos desearle un muy feliz cumpleaños a:\n\n✨ {users} ✨",
        "bday_invalid": "Fecha inválida.",
        "bday_privacy": "Configuración Actualizada",
        "bday_visible": "✅ **Visible**",
        "bday_hidden": "🔕 **Oculto**",
        "bday_list_title": "Próximos Cumpleaños 🍰",
        "bday_list_empty": "No hay cumpleaños registrados.",
        "bday_today": "🎂 **¡HOY!** - {user}",
        "bday_soon": "📅 `{date}` - **{user}** (en {days} días)",

        # --- ROLES ---
        "role_btn_success": "✅ Botón de rol creado exitosamente.",
        "role_not_found": "❌ El rol asociado a este botón ya no existe.",
        "role_removed": "❌ Te he quitado el rol **{role}**.",
        "role_added": "✅ Te he dado el rol **{role}**.",
        
        # --- UTILS (Chaos, Mención, Bienvenida, Backup) ---
        "chaos_bang": "¡Pum! **{user}** ha tenido mala suerte ({prob}%).\nEstarás aislado por 1 minuto.",
        "mention_response_default": "¡Hola! Soy **{bot}**.\nUsa `/help` para ver mis comandos.",
        "welcome_title": "¡Bienvenido/a {user}!",
        "welcome_desc": "Hola {mention}, gracias por unirte a **{server}**.",
        "goodbye_title": "Un usuario ha partido",
        "goodbye_desc": "{user} ha abandonado el servidor.",
        
        # --- VOICE (NUEVO) ---
        "voice_join": "✅ Conectado a **{channel}**. (Modo AFK)",
        "voice_leave": "👋 Desconectado del canal de voz.",
        "voice_error_user": "❌ Debes estar en un canal de voz primero.",
        "voice_error_bot": "❌ Ya estoy conectado en otro canal.",
        "voice_error_perms": "❌ No tengo permisos para entrar a ese canal.",
        
        # --- AYUDA ---
        "help_title": "Panel de Ayuda",
        "help_desc": "Hola **{user}**. Usa el menú de abajo para explorar las funciones.",
        "help_stats": "• **{cats}** Categorías\n• **{cmds}** Comandos",
        "help_categories": "📂 Categorías Disponibles",
        "help_module_title": "Módulo {module}",
        "help_module_desc": "Comandos disponibles en **{module}**:",
        "help_no_cmds": "No hay comandos disponibles.",
        "help_placeholder": "Selecciona una categoría...",
        "help_home": "Inicio",
        "help_home_desc": "Volver al panel principal",
        
        # --- STATUS (NUEVO) ---
        "status_add": "✅ Estado añadido: **{text}** ({type})",
        "status_deleted": "🗑️ Estado eliminado correctamente.",
        "status_empty": "⚠️ No hay estados configurados.",
        "status_placeholder": "Selecciona un estado para eliminar...",
        "status_list_title": "📜 Estados Activos",
        "status_list_desc": "El bot rotará entre estos estados:",
        
        # --- CONFIGURACIÓN ---
        "setup_success": "Configuración Actualizada",
        "setup_desc": "✅ {type} configurado exitosamente en: {value}",
        "setup_msg_updated": "✅ Mensaje actualizado.",
        "setup_autorol_on": "✅ Auto-Rol activado: {role}",
        "setup_autorol_off": "⚪ Auto-Rol desactivado.",
        "setup_chaos_desc": "{status}\n🔫 Probabilidad: **{prob}%**",
        "lang_success": "Idioma cambiado a **Español** 🇪🇸"
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
        "jumbo_invalid": "That doesn't look like a valid emoji.",
        "choice_title": "I decided",
        "choice_desc": "Between **{a}** and **{b}**, I choose:\n\n👉 **{result}**",
        "confess_title": "🤫 New Confession",
        "confess_sent": "Your secret has been published in {channel}.",

        # --- LEVELS & PROFILE ---
        "rank_title": "{user}'s Rank",
        "rank_no_data": "No XP data found.",
        "level_up_default": "🎉 Congrats {user}! You reached **Level {level}** in {server} 🆙",
        "leaderboard_title": "🏆 Top XP: {server}",
        "leaderboard_empty": "No one has experience in this server yet.",
        "profile_title": "{user}'s Card",
        "profile_desc": "No description.",
        "profile_no_bday": "Not set",
        "profile_server_stats": "**--- Server Stats ---**",
        "profile_custom_msgs": "--- Custom Messages ---",
        "profile_update_success": "Profile Updated",
        "profile_desc_saved": "Your description has been saved.",
        "profile_msg_saved": "Your message has been set.",
        
        # --- REBIRTH SYSTEM ---
        "rebirth_success": "✨ **REBIRTH COMPLETED!** ✨\nYou sacrificed level 100+ to be reborn. You now have **{rebirths}** Rebirth(s).\nYour level is back to 1.",
        "rebirth_fail_level": "❌ You are not ready yet. You need **Level 100** minimum (You are level {level}).",
        "rebirth_fail_generic": "❌ Rebirth could not be completed.",
        "rebirth_status": "🌀 Rebirths: {count}",

        # --- SIMULATION ---
        "simulation_title": "🔮 Event Simulation: {event}",
        "simulation_footer": "This is a test message only visible to you.",
        "sim_welcome": "Welcome",
        "sim_level": "Level Up",
        "sim_birthday": "Birthday",
        "sim_invalid": "❌ Invalid event. Use: `welcome`, `level`, `birthday`.",
        
        # --- BACKUP ---
        "backup_disabled": "⚠️ Backup sending to owner is disabled in settings.",
        
        # --- BIRTHDAY ---
        "bday_title": "🎉 Happy Birthday! 🎂",
        "bday_saved": "Date saved! **{date}**",
        "bday_removed": "Your birthday has been removed.",
        "bday_server_default": "Today is a special day. We want to wish a very happy birthday to:\n\n✨ {users} ✨",
        "bday_invalid": "Invalid date.",
        "bday_privacy": "Configuration Updated",
        "bday_visible": "✅ **Visible**",
        "bday_hidden": "🔕 **Hidden**",
        "bday_list_title": "Upcoming Birthdays 🍰",
        "bday_list_empty": "No birthdays registered.",
        "bday_today": "🎂 **TODAY!** - {user}",
        "bday_soon": "📅 `{date}` - **{user}** (in {days} days)",

        # --- ROLES ---
        "role_btn_success": "✅ Role button created successfully.",
        "role_not_found": "❌ The role associated with this button no longer exists.",
        "role_removed": "❌ Removed role **{role}**.",
        "role_added": "✅ Added role **{role}**.",
        
        # --- UTILS ---
        "chaos_bang": "Bang! **{user}** ran out of luck ({prob}%).\nPunishment: 1 minute timeout.",
        "mention_response_default": "Hi! I am **{bot}**.\nUse `/help` to see my commands.",
        "welcome_title": "Welcome {user}!",
        "welcome_desc": "Hi {mention}, thanks for joining **{server}**.",
        "goodbye_title": "A user has left",
        "goodbye_desc": "{user} has left the server.",
        
        # --- VOICE (NEW) ---
        "voice_join": "✅ Connected to **{channel}**. (AFK Mode)",
        "voice_leave": "👋 Disconnected from voice channel.",
        "voice_error_user": "❌ You need to be in a voice channel first.",
        "voice_error_bot": "❌ I am already connected somewhere else.",
        "voice_error_perms": "❌ I don't have permissions to join that channel.",
        
        # --- HELP ---
        "help_title": "Help Panel",
        "help_desc": "Hello **{user}**. Use the menu below to explore features.",
        "help_stats": "• **{cats}** Categories\n• **{cmds}** Commands",
        "help_categories": "📂 Available Categories",
        "help_module_title": "Module {module}",
        "help_module_desc": "Commands available in **{module}**:",
        "help_no_cmds": "No commands available.",
        "help_placeholder": "Select a category...",
        "help_home": "Home",
        "help_home_desc": "Return to main panel",
        
        # --- STATUS (NUEVO) ---
        "status_add": "✅ Status added: **{text}** ({type})",
        "status_deleted": "🗑️ Status deleted.",
        "status_empty": "⚠️ No statuses found.",
        "status_placeholder": "Select a status to delete...",
        "status_list_title": "📜 Active Statuses",
        "status_list_desc": "The bot will rotate through these:",
        
        # --- CONFIGURATION ---
        "setup_success": "Configuration Updated",
        "setup_desc": "✅ {type} successfully set to: {value}",
        "setup_msg_updated": "✅ Message updated.",
        "setup_autorol_on": "✅ Auto-Role enabled: {role}",
        "setup_autorol_off": "⚪ Auto-Role disabled.",
        "setup_chaos_desc": "{status}\n🔫 Probability: **{prob}%**",
        "lang_success": "Language changed to **English** 🇺🇸"
    }
}