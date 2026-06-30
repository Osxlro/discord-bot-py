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
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify"
        }
        url = "https://discord.com/api/oauth2/authorize?" + urllib.parse.urlencode(params)
        return RedirectResponse(url)

    @app.get("/auth/callback")
    async def auth_callback(request: Request, code: str = None):
        if not code:
            return RedirectResponse("/profile?error=no_code")
            
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
            
        request.session["user"] = {
            "id": user_id,
            "username": username,
            "avatar_url": avatar_url
        }
        
        return RedirectResponse("/profile")

    @app.get("/auth/logout")
    async def auth_logout(request: Request):
        request.session.clear()
        return RedirectResponse("/profile")

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
        
        # Validar y actualizar descripción
        if description is not None:
            # Sanitizar y limitar a 200
            desc = description.strip()[:200]
            await UserRepository.update_description(user_id, desc)
            
        # Validar y actualizar cumpleaños (DD-MM)
        if birthday:
            bday = birthday.strip()
            # Validar formato DD-MM
            import re
            if re.match(r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])$", bday):
                await UserRepository.set_user_birthday(user_id, bday, celebrate=bool(celebrate))
            elif bday.lower() in ("reset", "none", ""):
                await UserRepository.set_user_birthday(user_id, None, celebrate=False)
        else:
            # Si no se pasó bday, actualizar solo celebrate
            await database.execute("UPDATE users SET celebrate = ? WHERE user_id = ?", (celebrate, user_id))
            
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
                    "user_id": user_id, "coins": 0, "description": "Sin descripción.", "birthday": None, "celebrate": 1
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
                
            ctx.update({
                "user_data": user_data,
                "inventory": inventory_resolved,
                "guilds_data": guilds_data
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
        
    return app
