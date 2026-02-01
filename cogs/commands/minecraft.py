import discord
import logging
from discord.ext import commands
from aiohttp import web
from config import settings
from services import lang_service

logger = logging.getLogger(__name__)

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
        if not settings.MINECRAFT_CONFIG.get("ENABLED", True):
            return

        app = web.Application()
        app.router.add_post('/minecraft/update', self.handle_update)
        app.router.add_post('/minecraft/chat_in', self.handle_chat_in) # Nuevo endpoint
        app.router.add_get('/minecraft/read', self.handle_read)
        
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        
        # Puerto desde settings
        port = settings.MINECRAFT_CONFIG.get("PORT", 5058)
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()
        logger.info(f"🌍 Bridge Minecraft online en puerto {port}")

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
        except Exception as e:
            logger.error(f"Error recibiendo update Minecraft: {e}")
            return web.Response(status=400)

    async def handle_chat_in(self, request):
        """Recibe mensajes de chat DESDE Minecraft"""
        try:
            data = await request.json()
            default_name = settings.MINECRAFT_CONFIG.get("DEFAULT_NAME", "Steve")
            autor = data.get("autor", default_name)
            contenido = data.get("contenido", "")
            
            # Si tenemos un canal configurado, enviamos el mensaje allí
            if self.chat_channel_id:
                channel = self.bot.get_channel(self.chat_channel_id)
                if channel:
                    guild_id = channel.guild.id
                    lang = await lang_service.get_guild_lang(guild_id)
                    msg = lang_service.get_text("mc_chat_format", lang, user=autor, content=contenido)
                    await channel.send(msg)
            
            return web.Response(text="Enviado")
        except Exception as e:
            logger.error(f"Error chat in: {e}")
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
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        self.chat_channel_id = ctx.channel.id
        logger.info(f"Minecraft Bridge vinculado al canal {ctx.channel.id} por {ctx.author}")
        msg = lang_service.get_text("mc_bridge_set", lang, channel=ctx.channel.mention)
        await ctx.send(msg, ephemeral=True)

    @commands.hybrid_command(name="estadomc", description="Muestra estadísticas detalladas del jugador")
    async def estado(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        stats = self.player_stats
        if not stats:
            msg = lang_service.get_text("mc_no_stats", lang)
            return await ctx.send(msg, ephemeral=True)

        title = lang_service.get_text("mc_stats_title", lang, player=stats.get('jugador'))
        embed = discord.Embed(title=title, color=settings.COLORS["MINECRAFT"])
        unknown = lang_service.get_text("mc_unknown", lang)
        
        # Fila 1: Vitales
        embed.add_field(name=lang_service.get_text("mc_field_life", lang), value=f"{stats.get('vida', 0):.1f}", inline=True)
        embed.add_field(name=lang_service.get_text("mc_field_food", lang), value=str(stats.get('comida', 0)), inline=True)
        embed.add_field(name=lang_service.get_text("mc_field_armor", lang), value=str(stats.get('armadura', 0)), inline=True)
        
        # Fila 2: Progreso
        embed.add_field(name=lang_service.get_text("mc_field_xp", lang), value=str(stats.get('xp', 0)), inline=True)
        embed.add_field(name=lang_service.get_text("mc_field_coords", lang), value=stats.get('coords', unknown), inline=True)
        embed.add_field(name=lang_service.get_text("mc_field_biome", lang), value=stats.get('bioma', unknown).replace("minecraft:", "").title(), inline=True)

        # Fila 3: Ubicación
        embed.add_field(name=lang_service.get_text("mc_field_world", lang), value=stats.get('mundo', unknown), inline=False)
        
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="mc", description="Envía mensaje al juego")
    async def mc(self, ctx: commands.Context, mensaje: str):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        self.pending_messages.append({"autor": ctx.author.display_name, "mensaje": mensaje})
        
        # Optimización: Limitar la cola para evitar fugas de memoria si el servidor MC cae
        if len(self.pending_messages) > 50:
            self.pending_messages.pop(0)
            
        logger.info(f"Mensaje enviado a MC por {ctx.author}: {mensaje}")
        msg = lang_service.get_text("mc_msg_sent", lang, message=mensaje)
        await ctx.reply(msg, ephemeral=True)
        # Si es el canal bridge, borramos el comando del usuario para que se vea limpio (opcional)
        if ctx.channel.id == self.chat_channel_id:
            try: await ctx.message.delete()
            except: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Minecraft(bot))