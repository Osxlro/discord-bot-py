import uvicorn
import asyncio
import logging

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
