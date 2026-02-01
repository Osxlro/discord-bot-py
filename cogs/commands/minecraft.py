import discord
from discord.ext import commands
from aiohttp import web
import os

class Minecraft(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.site = None
        self.runner = None
        self.player_stats = {} 
        self.pending_messages = []
        # ID del canal donde se enviará el chat de Minecraft (Opcional: configúralo con un comando)
        self.chat_channel_id = None

    async def cog_load(self):
        app = web.Application()
        app.router.add_post('/minecraft/update', self.handle_update)
        app.router.add_post('/minecraft/chat_in', self.handle_chat_in) # Nuevo endpoint
        app.router.add_get('/minecraft/read', self.handle_read)
        
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        
        # Puerto configurable o por defecto 8080 (Para Cybrancee usa os.environ.get("PORT"))
        self.site = web.TCPSite(self.runner, '0.0.0.0', 5058)
        await self.site.start()
        # print(f"🌍 Bridge Minecraft online en puerto {port}")

    async def cog_unload(self):
        if self.site: await self.site.stop()
        if self.runner: await self.runner.cleanup()

    # --- ENDPOINTS ---
    
    async def handle_update(self, request):
        """Recibe estadísticas (Vida, Bioma, XP, etc)"""
        try:
            data = await request.json()
            self.player_stats = data
            return web.Response(text="OK")
        except:
            return web.Response(status=400)

    async def handle_chat_in(self, request):
        """Recibe mensajes de chat DESDE Minecraft"""
        try:
            data = await request.json()
            autor = data.get("autor", "Steve")
            contenido = data.get("contenido", "")
            
            # Si tenemos un canal configurado, enviamos el mensaje allí
            if self.chat_channel_id:
                channel = self.bot.get_channel(self.chat_channel_id)
                if channel:
                    await channel.send(f"**🧱 <{autor}>** {contenido}")
            
            return web.Response(text="Enviado")
        except Exception as e:
            print(f"Error chat in: {e}")
            return web.Response(status=400)

    async def handle_read(self, request):
        if self.pending_messages:
            msg = self.pending_messages.pop(0)
            return web.json_response(msg)
        return web.json_response({})

    # --- COMANDOS DISCORD ---

    @commands.hybrid_command(name="setbridgemc", description="Establece este canal para recibir el chat de Minecraft")
    @commands.has_permissions(administrator=True)
    async def set_bridge(self, ctx: commands.Context):
        self.chat_channel_id = ctx.channel.id
        await ctx.send(f"✅ Canal de chat vinculado: {ctx.channel.mention}")

    @commands.hybrid_command(name="estadomc", description="Muestra estadísticas detalladas del jugador")
    async def estado(self, ctx: commands.Context):
        stats = self.player_stats
        if not stats:
            return await ctx.send("❌ No hay datos. ¿El jugador está conectado?")

        embed = discord.Embed(title=f"Estado de {stats.get('jugador')}", color=discord.Color.blue())
        
        # Fila 1: Vitales
        embed.add_field(name="❤️ Vida", value=f"{stats.get('vida', 0):.1f}", inline=True)
        embed.add_field(name="🍖 Comida", value=str(stats.get('comida', 0)), inline=True)
        embed.add_field(name="🛡️ Armadura", value=str(stats.get('armadura', 0)), inline=True)
        
        # Fila 2: Progreso
        embed.add_field(name="✨ Nivel XP", value=str(stats.get('xp', 0)), inline=True)
        embed.add_field(name="📍 Coordenadas", value=stats.get('coords', '?'), inline=True)
        embed.add_field(name="🌲 Bioma", value=stats.get('bioma', '?').replace("minecraft:", "").title(), inline=True)

        # Fila 3: Ubicación
        embed.add_field(name="🌎 Mundo", value=stats.get('mundo', '?'), inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="mc", description="Envía mensaje al juego")
    async def mc(self, ctx: commands.Context, mensaje: str):
        self.pending_messages.append({"autor": ctx.author.display_name, "mensaje": mensaje})
        await ctx.reply(f"📨 Enviado: `{mensaje}`", ephemeral=True)
        # Si es el canal bridge, borramos el comando del usuario para que se vea limpio (opcional)
        if ctx.channel.id == self.chat_channel_id:
            try: await ctx.message.delete()
            except: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Minecraft(bot))