from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pathlib

# Setup templates directory
current_dir = pathlib.Path(__file__).parent.resolve()
templates_dir = current_dir / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

def create_app() -> FastAPI:
    app = FastAPI(title="Friday Bot Web Portal")
    
    # Store dynamic state
    app.state.bot = None
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        bot = getattr(request.app.state, "bot", None)
        
        # Default fallback values if bot is not yet ready or connected
        bot_name = "Friday Bot"
        bot_avatar = "https://img.pyrocdn.com/dbKUgahg.png"
        guilds_count = 0
        users_count = 0
        commands_count = 0
        is_ready = False
        
        if bot and bot.is_ready():
            is_ready = True
            bot_name = str(bot.user.name)
            bot_avatar = bot.user.display_avatar.url
            guilds_count = len(bot.guilds)
            users_count = sum(guild.member_count for guild in bot.guilds if guild.member_count)
            # Count prefix commands + slash commands
            commands_count = len(bot.commands) + len(bot.tree.get_commands())
            
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "bot_name": bot_name,
                "bot_avatar": bot_avatar,
                "guilds_count": guilds_count,
                "users_count": users_count,
                "commands_count": commands_count,
                "is_ready": is_ready
            }
        )
        
    return app
