import uvicorn
import asyncio
import logging
import logging.handlers
import pathlib

logger = logging.getLogger("web.server")

class WebServer:
    def __init__(self, app, host: str = "0.0.0.0", port: int = 5058):
        self.config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            loop="asyncio"
        )
        self.server = uvicorn.Server(self.config)
        self.task = None
        self._setup_logging()

    def _setup_logging(self):
        # Configure separated logs for web portal
        data_dir = pathlib.Path("./data")
        data_dir.mkdir(exist_ok=True)
        web_log_path = data_dir / "web.log"
        
        # Clean up old web log on startup
        try:
            if web_log_path.exists():
                web_log_path.unlink()
        except Exception:
            pass
            
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # 5MB rotating file handler
        web_handler = logging.handlers.RotatingFileHandler(
            filename=web_log_path,
            encoding="utf-8",
            maxBytes=5*1024*1024,
            backupCount=5
        )
        web_handler.setFormatter(formatter)
        web_handler.setLevel(logging.INFO)
        
        # Redirect uvicorn and web loggers to web.log and disable propagation to root (discord.log)
        web_loggers = ["web", "web.server", "uvicorn", "uvicorn.error", "uvicorn.access"]
        for logger_name in web_loggers:
            l = logging.getLogger(logger_name)
            l.setLevel(logging.INFO)
            # Avoid adding multiple duplicate handlers if initialized multiple times
            for h in list(l.handlers):
                l.removeHandler(h)
            l.addHandler(web_handler)
            l.propagate = False

    def start(self):
        logger.info(f"🌐 Iniciando servidor web en http://{self.config.host}:{self.config.port}...")
        self.task = asyncio.create_task(self.server.serve())

    async def stop(self):
        if self.task:
            logger.info("🛑 Deteniendo servidor web...")
            self.server.should_exit = True
            await self.server.shutdown()
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            logger.info("🌐 Servidor web detenido correctamente.")
