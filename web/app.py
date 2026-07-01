from fastapi import FastAPI, Request, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from web.config import web_settings
from services.features import web_bridge_service
from services.repositories.user_repository import UserRepository
from services.repositories.xp_repository import calculate_xp_required
from services.core import database, db_service
import pathlib
import time
import aiohttp
import urllib.parse
import secrets
import logging

logger = logging.getLogger("web.app")

# Setup directories
current_dir = pathlib.Path(__file__).parent.resolve()
templates_dir = current_dir / "templates"
static_dir = current_dir / "static"

templates = Jinja2Templates(directory=str(templates_dir))

# Configuración del Limitador de Peticiones en memoria
RATE_LIMIT_REQUESTS = 30  # Máximo de peticiones
RATE_LIMIT_WINDOW = 60    # Ventana en segundos
ip_request_history = {}   # IP -> lista de timestamps

def get_common_context(request: Request, active_page: str = "") -> dict:
    """Genera el contexto base para todas las plantillas Jinja2."""
    bot = getattr(request.app.state, "bot", None)
    bot_name = "Friday Bot"
    bot_avatar = "https://img.pyrocdn.com/dbKUgahg.png"
    is_ready = False
    
    if bot and bot.is_ready():
        is_ready = True
        bot_name = str(bot.user.name)
        bot_avatar = bot.user.display_avatar.url
        
    user = request.session.get("user") if hasattr(request, "session") else None
        
    return {
        "request": request,
        "bot_name": bot_name,
        "bot_avatar": bot_avatar,
        "is_ready": is_ready,
        "active_page": active_page,
        "web_domain": web_settings.WEB_DOMAIN,
        "web_port": web_settings.WEB_PORT,
        "expose_port": web_settings.WEB_EXPOSE_PORT,
        "user": user
    }

def create_app() -> FastAPI:
    app = FastAPI(title="Friday Bot Web Portal")
    
    # Store dynamic state
    app.state.bot = None
    
    # Montar archivos estáticos
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # 1. Configuración de CORS
    origins = [
        "http://localhost",
        "http://localhost:5058",
        "http://127.0.0.1",
        "http://127.0.0.1:5058",
        f"http://{web_settings.WEB_DOMAIN}",
        f"https://{web_settings.WEB_DOMAIN}",
        f"http://{web_settings.WEB_DOMAIN}:{web_settings.WEB_PORT}",
        f"https://{web_settings.WEB_DOMAIN}:{web_settings.WEB_PORT}"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # 1.5. Configuración de SessionMiddleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=web_settings.SESSION_SECRET_KEY,
        session_cookie="friday_session",
        same_site="lax",
        https_only=web_settings.WEB_SECURE_COOKIES
    )
    
    # 2. Middleware de Rate Limiting con soporte para IP Real detrás de Cloudflare
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Intentar extraer cabezales de Cloudflare
        cf_ip = request.headers.get("cf-connecting-ip")
        x_forwarded = request.headers.get("x-forwarded-for")
        
        if cf_ip:
            client_ip = cf_ip
        elif x_forwarded:
            client_ip = x_forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
            
        now = time.time()
        
        # Obtener historial de peticiones de esta IP y limpiarlo de eventos expirados
        history = ip_request_history.get(client_ip, [])
        history = [t for t in history if now - t < RATE_LIMIT_WINDOW]
        
        if len(history) >= RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."}
            )
            
        history.append(now)
        ip_request_history[client_ip] = history
        
        return await call_next(request)
        
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        bot = getattr(request.app.state, "bot", None)
        ctx = get_common_context(request, active_page="index")
        
        stats = {
            "latency": 0.0,
            "uptime_seconds": 0.0,
            "uptime_str": "0m",
            "guilds_count": 0,
            "users_count": 0,
            "commands_count": 0
        }
        if bot and bot.is_ready():
            stats = web_bridge_service.get_bot_status(bot)
            
        ctx.update(stats)
        return templates.TemplateResponse(request, "index.html", ctx)
        
    @app.get("/commands", response_class=HTMLResponse)
    async def commands_page(request: Request):
        bot = getattr(request.app.state, "bot", None)
        ctx = get_common_context(request, active_page="commands")
        
        categories = {}
        if bot:
            categories = web_bridge_service.get_commands_by_category(bot)
            
        ctx["categories"] = categories
        return templates.TemplateResponse(request, "commands.html", ctx)
        
    @app.get("/docs", response_class=HTMLResponse)
    async def docs_page(request: Request):
        ctx = get_common_context(request, active_page="docs")
        return templates.TemplateResponse(request, "docs.html", ctx)

    # --- RUTAS DE DISCORD OAUTH2 ---
    @app.get("/auth/login")
    async def auth_login(request: Request):
        bot = getattr(request.app.state, "bot", None)
        client_id = web_settings.DISCORD_CLIENT_ID or (str(bot.user.id) if bot and bot.is_ready() else "")
        # Determinar URI de redirección dinámica según el host de la petición
        host = request.headers.get("host", f"{web_settings.WEB_DOMAIN}:{web_settings.WEB_PORT}")
        scheme = "https" if web_settings.WEB_SECURE_COOKIES or request.headers.get("x-forwarded-proto") == "https" else "http"
        redirect_uri = f"{scheme}://{host}/auth/callback"
        
        # Generar un token de estado aleatorio para prevenir ataques CSRF
        state = secrets.token_urlsafe(16)
        request.session["oauth_state"] = state
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify guilds",
            "state": state
        }
        url = "https://discord.com/api/oauth2/authorize?" + urllib.parse.urlencode(params)
        return RedirectResponse(url)

    @app.get("/auth/callback")
    async def auth_callback(request: Request, code: str = None, state: str = None):
        if not code:
            return RedirectResponse("/profile?error=no_code")
            
        # Validar el token de estado para prevenir ataques CSRF
        session_state = request.session.pop("oauth_state", None)
        if not session_state or state != session_state:
            return HTMLResponse("Error de seguridad: verificación de estado (CSRF) fallida.", status_code=400)
            
        bot = getattr(request.app.state, "bot", None)
        client_id = web_settings.DISCORD_CLIENT_ID or (str(bot.user.id) if bot and bot.is_ready() else "")
            
        host = request.headers.get("host", f"{web_settings.WEB_DOMAIN}:{web_settings.WEB_PORT}")
        scheme = "https" if web_settings.WEB_SECURE_COOKIES or request.headers.get("x-forwarded-proto") == "https" else "http"
        redirect_uri = f"{scheme}://{host}/auth/callback"
        
        # Intercambiar código por Access Token
        data = {
            "client_id": client_id,
            "client_secret": web_settings.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://discord.com/api/oauth2/token", data=data, headers=headers) as resp:
                if resp.status != 200:
                    err_body = await resp.text()
                    return HTMLResponse(f"Error obteniendo token de Discord ({resp.status}): {err_body}", status_code=400)
                token_data = await resp.json()
                access_token = token_data.get("access_token")
                
            # Obtener datos del usuario
            user_headers = {
                "Authorization": f"Bearer {access_token}"
            }
            async with session.get("https://discord.com/api/users/@me", headers=user_headers) as resp:
                if resp.status != 200:
                    return HTMLResponse("Error obteniendo datos del usuario en Discord", status_code=400)
                discord_user = await resp.json()
                
            # Obtener servidores del usuario
            async with session.get("https://discord.com/api/users/@me/guilds", headers=user_headers) as resp:
                if resp.status == 200:
                    discord_guilds = await resp.json()
                else:
                    discord_guilds = []
                
        # Guardar en sesión
        user_id = int(discord_user["id"])
        username = discord_user["username"]
        avatar_hash = discord_user.get("avatar")
        
        if avatar_hash:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
        else:
            # Avatar por defecto
            discriminator = int(discord_user.get("discriminator", "0"))
            default_avatar_index = (user_id >> 22) % 6 if discriminator == 0 else discriminator % 5
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_avatar_index}.png"
            
        # Filtrar servidores administrados y mutuos con el bot
        admin_guilds = []
        mutual_guilds = []
        bot = getattr(request.app.state, "bot", None)
        
        for g in discord_guilds:
            g_id = int(g["id"])
            is_owner = g.get("owner", False)
            perms = int(g.get("permissions", 0))
            # Administrador (0x8) o Gestionar Servidor (0x20)
            if is_owner or (perms & 0x8) == 0x8 or (perms & 0x20) == 0x20:
                admin_guilds.append(g_id)
            # Servidores mutuos con el bot
            if bot and bot.get_guild(g_id):
                mutual_guilds.append(g_id)
            
        request.session["user"] = {
            "id": user_id,
            "username": username,
            "avatar_url": avatar_url
        }
        request.session["admin_guilds"] = admin_guilds
        request.session["mutual_guilds"] = mutual_guilds
        
        return RedirectResponse("/profile")

    @app.get("/auth/logout")
    async def auth_logout(request: Request):
        request.session.clear()
        return RedirectResponse("/profile")

    async def send_profile_update_dm(bot, user_id: int, description: str, birthday: str, celebrate: bool, lang: str):
        try:
            user = bot.get_user(user_id)
            if not user:
                user = await bot.fetch_user(user_id)
            if user:
                from services.core import lang_service
                from services.utils import embed_service
                
                title = lang_service.get_text("web_dm_notification_title", lang)
                desc_text = lang_service.get_text(
                    "web_dm_notification_desc_text", 
                    lang, 
                    bio=description or "-", 
                    bday=birthday or "-", 
                    cel="Sí" if celebrate else "No"
                )
                embed = embed_service.info(
                    title=title,
                    description=desc_text,
                    lite=False
                )
                await user.send(embed=embed)
        except Exception as e:
            logger.exception(f"Error al enviar DM de notificacion a {user_id}: {e}")

    @app.post("/profile/update")
    async def profile_update(
        request: Request,
        description: str = Form(None),
        birthday: str = Form(None),
        celebrate: int = Form(1)
    ):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/profile?error=unauthorized", status_code=status.HTTP_303_SEE_OTHER)
            
        user_id = user["id"]
        
        # Procesar checkbox web_notifications
        form_data = await request.form()
        web_notif_val = 1 if "web_notifications" in form_data else 0
        
        # Obtener datos antiguos para comparar cambios
        old_data = await UserRepository.get_user_data(user_id)
        if not old_data:
            old_data = {
                "description": "",
                "birthday": None,
                "celebrate": 1,
                "web_notifications": 1
            }
            
        desc_val = old_data.get("description")
        # Validar y actualizar descripción
        if description is not None:
            desc_val = description.strip()[:200]
            await UserRepository.update_description(user_id, desc_val)
            
        # Validar y actualizar cumpleaños (DD-MM)
        bday_val = old_data.get("birthday")
        celebrate_val = bool(celebrate)
        if birthday:
            bday_val = birthday.strip()
            # Validar formato DD-MM
            import re
            if re.match(r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])$", bday_val):
                await UserRepository.set_user_birthday(user_id, bday_val, celebrate=celebrate_val)
            elif bday_val.lower() in ("reset", "none", ""):
                bday_val = None
                await UserRepository.set_user_birthday(user_id, None, celebrate=False)
        else:
            # Si no se pasó bday, actualizar solo celebrate
            await database.execute("UPDATE users SET celebrate = ? WHERE user_id = ?", (celebrate, user_id))
            
        # Guardar preferencia de notificaciones
        await UserRepository.update_user_data(user_id, {"web_notifications": web_notif_val})
        
        # Detectar cambios reales
        changed = (
            desc_val != old_data.get("description") or
            bday_val != old_data.get("birthday") or
            celebrate_val != bool(old_data.get("celebrate")) or
            web_notif_val != old_data.get("web_notifications")
        )
        
        bot = getattr(request.app.state, "bot", None)
        if changed and web_notif_val == 1 and bot:
            # Detectar idioma del servidor/usuario (por defecto 'es')
            lang = "es"
            bot.loop.create_task(
                send_profile_update_dm(bot, user_id, desc_val, bday_val, celebrate_val, lang)
            )
            
        return RedirectResponse("/profile?success=updated", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/profile/delete-data")
    async def profile_delete_data(request: Request, confirm_name: str = Form("")):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/profile?error=unauthorized", status_code=status.HTTP_303_SEE_OTHER)
            
        if confirm_name.strip() != user["username"]:
            return RedirectResponse("/profile?error=delete_verification_failed", status_code=status.HTTP_303_SEE_OTHER)
            
        user_id = user["id"]
        
        # Borrar registros de base de datos
        await database.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        
        # Limpiar sesión
        request.session.clear()
        
        return RedirectResponse("/profile?success=deleted", status_code=status.HTTP_303_SEE_OTHER)
        
    @app.get("/profile", response_class=HTMLResponse)
    async def profile_page(request: Request):
        bot = getattr(request.app.state, "bot", None)
        ctx = get_common_context(request, active_page="profile")
        
        user = ctx["user"]
        if user:
            user_id = user["id"]
            
            # 1. Obtener datos globales (monedas, biografía, cumpleaños)
            user_data = await UserRepository.get_user_data(user_id)
            if not user_data:
                # Si es la primera vez del usuario, crear un registro vacío en DB
                await database.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
                user_data = await UserRepository.get_user_data(user_id) or {
                    "user_id": user_id, "coins": 0, "description": "Sin descripción.", "birthday": None, "celebrate": 1, "web_notifications": 1
                }
                
            # 2. Obtener y resolver inventario
            inventory = await db_service.get_user_inventory(user_id)
            shop_items = await db_service.get_all_shop_items()
            shop_map = {item["item_id"]: item for item in shop_items}
            
            from services.features.shop_service import get_localized_field
            lang = "es" # Idioma por defecto de visualización
            
            inventory_resolved = []
            for item_id, qty in inventory.items():
                if qty <= 0: continue
                item_info = shop_map.get(item_id)
                if item_info:
                    emoji = item_info.get("emoji") or "📦"
                    name = get_localized_field(item_info, "names", lang)
                else:
                    emoji = "📦"
                    name = item_id.replace("_", " ").title()
                    
                inventory_resolved.append({
                    "item_id": item_id,
                    "quantity": qty,
                    "emoji": emoji,
                    "name": name
                })
                
            # 3. Obtener niveles y XP en todos los servidores
            guilds_data = []
            rows = await database.fetch_all("SELECT guild_id, level, xp, rebirths FROM guild_stats WHERE user_id = ?", (user_id,))
            for row in rows:
                g_id = row["guild_id"]
                guild = bot.get_guild(g_id) if bot else None
                guild_name = guild.name if guild else f"Servidor {g_id}"
                guild_icon = guild.icon.url if (guild and guild.icon) else None
                
                lvl = row["level"]
                xp_req = calculate_xp_required(lvl)
                xp_curr = row["xp"]
                progress_percent = min(100, int((xp_curr / xp_req) * 100)) if xp_req > 0 else 0
                
                guilds_data.append({
                    "guild_id": g_id,
                    "guild_name": guild_name,
                    "guild_icon": guild_icon,
                    "level": lvl,
                    "xp": xp_curr,
                    "xp_required": xp_req,
                    "rebirths": row["rebirths"],
                    "progress_percent": progress_percent
                })
                
            # Auto-grant "pioneer" badge y resolver insignias
            await UserRepository.grant_badge(user_id, "pioneer")
            from services.features import badge_service
            user_badges = await badge_service.get_resolved_badges(user_id, lang=lang)

            ctx.update({
                "user_data": user_data,
                "inventory": inventory_resolved,
                "guilds_data": guilds_data,
                "user_badges": user_badges
            })
            
        return templates.TemplateResponse(request, "profile.html", ctx)
        
    @app.get("/terms", response_class=HTMLResponse)
    async def terms_page(request: Request):
        ctx = get_common_context(request, active_page="terms")
        return templates.TemplateResponse(request, "terms.html", ctx)
        
    @app.get("/privacy", response_class=HTMLResponse)
    async def privacy_page(request: Request):
        ctx = get_common_context(request, active_page="privacy")
        return templates.TemplateResponse(request, "privacy.html", ctx)

    # --- SERVER SETUP DASHBOARD ---
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page(request: Request):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/auth/login")
            
        bot = getattr(request.app.state, "bot", None)
        user_admin_ids = request.session.get("admin_guilds", [])
        
        mutual_guilds = []
        if bot and bot.is_ready():
            for g_id in user_admin_ids:
                guild = bot.get_guild(g_id)
                if guild:
                    icon_url = guild.icon.url if guild.icon else None
                    mutual_guilds.append({
                        "id": str(guild.id),
                        "name": guild.name,
                        "icon_url": icon_url
                    })
                    
        ctx = get_common_context(request, active_page="dashboard")
        ctx.update({
            "mutual_guilds": mutual_guilds
        })
        return templates.TemplateResponse(request, "dashboard.html", ctx)

    @app.get("/dashboard/guild/{guild_id}", response_class=HTMLResponse)
    async def guild_setup_page(request: Request, guild_id: int):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/auth/login")
            
        user_admin_ids = request.session.get("admin_guilds", [])
        if guild_id not in user_admin_ids:
            return RedirectResponse("/dashboard?error=forbidden")
            
        bot = getattr(request.app.state, "bot", None)
        if not bot or not bot.is_ready():
            return RedirectResponse("/dashboard?error=bot_offline")
            
        guild = bot.get_guild(guild_id)
        if not guild:
            return RedirectResponse("/dashboard?error=guild_not_found")
            
        # Obtener canales de texto y roles para los dropdowns
        channels = [{"id": str(c.id), "name": c.name} for c in guild.text_channels]
        roles = [{"id": str(r.id), "name": r.name} for r in guild.roles if not r.is_default()]
        
        current_config = await db_service.get_guild_config(guild_id)
        
        config_resolved = {}
        for k, v in current_config.items():
            if k.endswith("_id"):
                config_resolved[k] = str(v)
            else:
                config_resolved[k] = v
                
        guild_icon = guild.icon.url if guild.icon else None
        
        ctx = get_common_context(request, active_page="dashboard")
        ctx.update({
            "guild_id": str(guild_id),
            "guild_name": guild.name,
            "guild_icon": guild_icon,
            "channels": channels,
            "roles": roles,
            "current_config": config_resolved
        })
        return templates.TemplateResponse(request, "guild_setup.html", ctx)

    @app.post("/dashboard/guild/{guild_id}/update")
    async def guild_setup_update(
        request: Request,
        guild_id: int,
        welcome_channel_id: int = Form(0),
        logs_channel_id: int = Form(0),
        confessions_channel_id: int = Form(0),
        birthday_channel_id: int = Form(0),
        minecraft_channel_id: int = Form(0),
        wordday_channel_id: int = Form(0),
        autorole_id: int = Form(0),
        wordday_role_id: int = Form(0),
        language: str = Form("es")
    ):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
            
        user_admin_ids = request.session.get("admin_guilds", [])
        if guild_id not in user_admin_ids:
            return RedirectResponse("/dashboard?error=forbidden", status_code=status.HTTP_303_SEE_OTHER)
            
        form_data = await request.form()
        chaos_enabled = 1 if "chaos_enabled" in form_data else 0
        
        try:
            chaos_prob_pct = float(form_data.get("chaos_probability", "1.0"))
            chaos_probability = max(0.1, min(100.0, chaos_prob_pct)) / 100.0
        except ValueError:
            chaos_probability = 0.01

        server_welcome_msg = form_data.get("server_welcome_msg", "").strip() or None
        server_goodbye_msg = form_data.get("server_goodbye_msg", "").strip() or None
        server_level_msg = form_data.get("server_level_msg", "").strip() or None
        server_birthday_msg = form_data.get("server_birthday_msg", "").strip() or None
        server_kick_msg = form_data.get("server_kick_msg", "").strip() or None
        server_ban_msg = form_data.get("server_ban_msg", "").strip() or None
        mention_response = form_data.get("mention_response", "").strip() or None

        updates = {
            "welcome_channel_id": welcome_channel_id,
            "logs_channel_id": logs_channel_id,
            "confessions_channel_id": confessions_channel_id,
            "birthday_channel_id": birthday_channel_id,
            "minecraft_channel_id": minecraft_channel_id,
            "wordday_channel_id": wordday_channel_id,
            "autorole_id": autorole_id,
            "wordday_role_id": wordday_role_id,
            "language": language,
            "chaos_enabled": chaos_enabled,
            "chaos_probability": chaos_probability,
            "server_welcome_msg": server_welcome_msg,
            "server_goodbye_msg": server_goodbye_msg,
            "server_level_msg": server_level_msg,
            "server_birthday_msg": server_birthday_msg,
            "server_kick_msg": server_kick_msg,
            "server_ban_msg": server_ban_msg,
            "mention_response": mention_response
        }
        
        await db_service.update_guild_config(guild_id, updates)
        return RedirectResponse(f"/dashboard/guild/{guild_id}?success=saved", status_code=status.HTTP_303_SEE_OTHER)

    # --- XP LEADERBOARD ---
    @app.get("/leaderboard", response_class=HTMLResponse)
    async def leaderboard_page(request: Request, guild_id: int = None):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/auth/login")
            
        bot = getattr(request.app.state, "bot", None)
        mutual_guild_ids = request.session.get("mutual_guilds", [])
        
        guilds = []
        if bot and bot.is_ready():
            for g in bot.guilds:
                if g.id in mutual_guild_ids:
                    guilds.append({
                        "id": str(g.id),
                        "name": g.name
                    })
                
        leaderboard_rows = []
        current_guild_id = None
        
        if guild_id and bot and bot.is_ready():
            if guild_id not in mutual_guild_ids:
                return RedirectResponse("/leaderboard?error=forbidden")
                
            guild = bot.get_guild(guild_id)
            if guild:
                current_guild_id = str(guild.id)
                from services.repositories.xp_repository import XpRepository
                rows = await XpRepository.get_leaderboard(guild_id, 50)
                
                for row in rows:
                    u_id = row["user_id"]
                    member = guild.get_member(u_id)
                    if not member:
                        member = bot.get_user(u_id)
                        if not member:
                            try:
                                member = await bot.fetch_user(u_id)
                            except Exception:
                                member = None
                                
                    username = member.name if member else f"ID: {u_id}"
                    avatar_url = member.display_avatar.url if member else "https://cdn.discordapp.com/embed/avatars/0.png"
                    
                    leaderboard_rows.append({
                        "username": username,
                        "avatar_url": avatar_url,
                        "rebirths": row.get("rebirths", 0),
                        "level": row.get("level", 1),
                        "xp": row.get("xp", 0)
                    })
                    
        ctx = get_common_context(request, active_page="leaderboard")
        ctx.update({
            "guilds": guilds,
            "current_guild_id": current_guild_id,
            "leaderboard_rows": leaderboard_rows
        })
        return templates.TemplateResponse(request, "leaderboard.html", ctx)

    # --- SHOP ENDPOINTS ---
    @app.get("/shop", response_class=HTMLResponse)
    async def shop_page(request: Request):
        items = await db_service.get_all_shop_items()
        
        user = request.session.get("user")
        user_coins = 0
        user_tickets = 0
        if user:
            user_id = user["id"]
            user_coins = await db_service.get_user_coins(user_id)
            row = await database.fetch_one("SELECT ticket_count FROM raffle_tickets WHERE user_id = ?", (user_id,))
            user_tickets = row["ticket_count"] if row else 0
            
        # Obtener total de boletos en juego
        row_total = await database.fetch_one("SELECT SUM(ticket_count) as total FROM raffle_tickets")
        total_tickets = row_total["total"] if (row_total and row_total["total"]) else 0
            
        lang = request.session.get("lang", "es")
        from services.features.shop_service import get_localized_field
        
        categories = {}
        for item in items:
            cat = item.get("category", "Otros")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "item_id": item["item_id"],
                "emoji": item["emoji"] or "📦",
                "cost": item["cost"],
                "name": get_localized_field(item, "names", lang),
                "description": get_localized_field(item, "descs", lang),
                "category": cat
            })
            
        ctx = get_common_context(request, active_page="shop")
        ctx.update({
            "user_coins": user_coins,
            "user_tickets": user_tickets,
            "total_tickets": total_tickets,
            "categories": categories
        })
        return templates.TemplateResponse(request, "shop.html", ctx)

    @app.post("/shop/buy")
    async def shop_buy(
        request: Request,
        item_id: str = Form(...),
        quantity: int = Form(1)
    ):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
            
        user_id = user["id"]
        lang = request.session.get("lang", "es")
        
        from services.features import shop_service
        success, err_msg, embed = await shop_service.process_purchase(user_id, item_id, quantity, lang)
        
        if success:
            return RedirectResponse("/shop?success=purchased", status_code=status.HTTP_303_SEE_OTHER)
        else:
            err_code = "insufficient_coins" if "coins" in (err_msg or "").lower() else urllib.parse.quote(err_msg or "error")
            return RedirectResponse(f"/shop?error={err_code}", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/shop/buy-ticket")
    async def shop_buy_ticket(
        request: Request,
        quantity: int = Form(1)
    ):
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
            
        user_id = user["id"]
        if quantity <= 0:
            return RedirectResponse("/shop?error=invalid_quantity", status_code=status.HTTP_303_SEE_OTHER)
            
        ticket_cost = 50
        total_cost = ticket_cost * quantity
        
        # Check coins
        user_coins = await db_service.get_user_coins(user_id)
        if user_coins < total_cost:
            return RedirectResponse("/shop?error=insufficient_coins", status_code=status.HTTP_303_SEE_OTHER)
            
        # Deduct coins and add tickets atomically
        try:
            query_coins = (
                "INSERT INTO users (user_id, coins) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET coins = coins + excluded.coins"
            )
            query_tickets = (
                "INSERT INTO raffle_tickets (user_id, ticket_count) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET ticket_count = ticket_count + excluded.ticket_count"
            )
            
            queries = [
                (query_coins, (user_id, -total_cost)),
                (query_tickets, (user_id, quantity))
            ]
            await database.execute_transaction(queries)
            return RedirectResponse("/shop?success=purchased", status_code=status.HTTP_303_SEE_OTHER)
        except Exception as e:
            logger.exception(f"Error al comprar boletos de loteria para {user_id}: {e}")
            return RedirectResponse("/shop?error=db_error", status_code=status.HTTP_303_SEE_OTHER)

    return app
