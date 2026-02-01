import discord
from discord.ext import commands
from discord import app_commands
from aiohttp import web
import asyncio

class MinecraftBridge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.site = None
        self.runner = None
        self.player_stats = {} 
        self.pending_messages = []

    async def cog_load(self):
        app = web.Application()
        app.router.add_post('/minecraft/update', self.handle_update)
        app.router.add_get('/minecraft/read', self.handle_read)
        
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        # Escuchamos en el puerto 8080 (mismo que pusimos en el Mod de Java)
        self.site = web.TCPSite(self.runner, 'localhost', 8080)
        await self.site.start()
        print("🌍 Servidor Bridge de Minecraft iniciado en puerto 8080")

    async def cog_unload(self):
        if self.site: await self.site.stop()
        if self.runner: await self.runner.cleanup()

    async def handle_update(self, request):
        """Recibe datos desde Minecraft"""
        try:
            data = await request.json()
            self.player_stats = data
            return web.Response(text="OK")
        except:
            return web.Response(status=400)

    async def handle_read(self, request):
        """Minecraft pregunta si hay mensajes nuevos"""
        if self.pending_messages:
            msg = self.pending_messages.pop(0)
            return web.json_response(msg)
        return web.json_response({})

    # --- Comandos de Discord ---

    @commands.hybrid_command(name="estado", description="Muestra el estado del jugador en Minecraft")
    async def estado(self, ctx: commands.Context):
        stats = self.player_stats
        if not stats:
            return await ctx.send("❌ No hay datos recientes. ¿Está el jugador conectado?")

        embed = discord.Embed(title=f"Estado de {stats.get('jugador', 'Desconocido')}", color=discord.Color.green())
        embed.add_field(name="❤️ Vida", value=f"{stats.get('vida', 0):.1f} / {stats.get('max_vida', 20)}", inline=True)
        embed.add_field(name="🛡️ Armadura", value=str(stats.get('armadura', 0)), inline=True)
        embed.add_field(name="🍗 Comida", value=str(stats.get('comida', 0)), inline=True)
        embed.add_field(name="🌎 Mundo", value=stats.get('mundo', '?'), inline=False)
        embed.add_field(name="🌌 Dimensión", value=stats.get('dimension', '?'), inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="mc", description="Envía un mensaje al chat de Minecraft")
    async def mc(self, ctx: commands.Context, mensaje: str):
        self.pending_messages.append({
            "autor": ctx.author.display_name,
            "mensaje": mensaje
        })
        await ctx.reply(f"📨 Enviado a Minecraft: `{mensaje}`", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(MinecraftBridge(bot))