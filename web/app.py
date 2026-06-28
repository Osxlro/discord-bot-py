from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from web.config import web_settings
import pathlib
import time

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
        
    return {
        "request": request,
        "bot_name": bot_name,
        "bot_avatar": bot_avatar,
        "is_ready": is_ready,
        "active_page": active_page
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
    
    # 2. Middleware de Rate Limiting
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
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
        
        # Agregar estadísticas específicas de index
        ctx["guilds_count"] = 0
        ctx["users_count"] = 0
        ctx["commands_count"] = 0
        
        if bot and bot.is_ready():
            ctx["guilds_count"] = len(bot.guilds)
            ctx["users_count"] = sum(guild.member_count for guild in bot.guilds if guild.member_count)
            ctx["commands_count"] = len(bot.commands) + len(bot.tree.get_commands())
            
        return templates.TemplateResponse(request, "index.html", ctx)
        
    @app.get("/commands", response_class=HTMLResponse)
    async def commands_page(request: Request):
        ctx = get_common_context(request, active_page="commands")
        return templates.TemplateResponse(request, "commands.html", ctx)
        
    @app.get("/docs", response_class=HTMLResponse)
    async def docs_page(request: Request):
        ctx = get_common_context(request, active_page="docs")
        return templates.TemplateResponse(request, "docs.html", ctx)
        
    @app.get("/profile", response_class=HTMLResponse)
    async def profile_page(request: Request):
        ctx = get_common_context(request, active_page="profile")
        return templates.TemplateResponse(request, "profile.html", ctx)
        
    return app
