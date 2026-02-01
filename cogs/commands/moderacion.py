import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from services import embed_service, lang_service, db_service
import datetime
import re

class Moderacion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _parse_time(self, time_str: str) -> int:
        time_regex = re.compile(r"(\d+)([smhd])")
        match = time_regex.match(time_str.lower())
        if not match: return 0
        val, unit = match.groups()
        val = int(val)
        if unit == 's': return val
        if unit == 'm': return val * 60
        if unit == 'h': return val * 3600
        if unit == 'd': return val * 86400
        return 0

    @commands.hybrid_command(name="clear", description="Borra mensajes del chat.")
    @app_commands.describe(cantidad="Número de mensajes")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, cantidad: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        # Usamos .get() de forma segura desde settings
        max_msg = settings.CONFIG.get("moderation_config", {}).get("max_clear_msg", 100)

        if cantidad > max_msg:
            await ctx.reply(embed=embed_service.error("Límite", f"Máximo {max_msg} mensajes.", lite=True), ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        
        try:
            # MEJORA: Control de error para mensajes viejos (>14 días)
            deleted = await ctx.channel.purge(limit=cantidad)
            count = len(deleted)
            
            title = lang_service.get_text("clear_success", lang)
            desc = lang_service.get_text("clear_desc", lang, count=count)
            await ctx.send(embed=embed_service.success(title, desc, lite=True), delete_after=5)
            
        except discord.HTTPException:
            # Si falla (generalmente por mensajes viejos), avisamos
            await ctx.send(embed=embed_service.warning("Aviso", "No puedo borrar mensajes de hace más de 14 días (Limitación de Discord).", lite=True), ephemeral=True)

    @commands.hybrid_command(name="aislar", description="Aísla (Timeout) a un usuario.")
    @app_commands.describe(usuario="Miembro", tiempo="Ej: 10m, 1h", razon="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, usuario: discord.Member, tiempo: str, razon: str = "Sin motivo"):
        if usuario.top_role >= ctx.author.top_role:
            await ctx.reply(embed=embed_service.error("Jerarquía", "❌ No puedes aislar a alguien con igual o mayor rango.", lite=True), ephemeral=True)
            return

        seconds = self._parse_time(tiempo)
        if seconds == 0:
            await ctx.reply(embed=embed_service.error("Formato", "❌ Tiempo inválido. Usa: `10m`, `1h`, `1d`.", lite=True), ephemeral=True)
            return
            
        try:
            duration = datetime.timedelta(seconds=seconds)
            await usuario.timeout(duration, reason=razon)
            await ctx.reply(embed=embed_service.success("Usuario Aislado", f"🔇 **{usuario.name}** aislado por **{tiempo}**.\n📝 Razón: {razon}"))
        except Exception as e:
            await ctx.reply(embed=embed_service.error("Error", str(e), lite=True), ephemeral=True)
    
    @commands.hybrid_command(name="quitaraislamiento", description="Retira el aislamiento.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, usuario: discord.Member):
        try:
            await usuario.timeout(None, reason="Manual")
            await ctx.reply(embed=embed_service.success("Libre", f"🔊 **{usuario.name}** ya puede hablar.", lite=True))
        except Exception as e:
            await ctx.reply(embed=embed_service.error("Error", str(e), lite=True), ephemeral=True)

    @commands.hybrid_command(name="kick", description="Expulsa a un miembro.")
    @app_commands.describe(usuario="Miembro", razon="Motivo")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, usuario: discord.Member, razon: str = "N/A"):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if usuario.id == ctx.author.id:
            await ctx.reply(embed=embed_service.warning("!", lang_service.get_text("error_self_action", lang), lite=True), ephemeral=True)
            return

        try:
            await usuario.kick(reason=razon)
            
            # --- OPTIMIZACIÓN: USAR CACHÉ EN LUGAR DE SQL DIRECTO ---
            # Antes: row = await db_service.fetch_one(...)
            config = await db_service.get_guild_config(ctx.guild.id)
            msg_custom = config.get('server_kick_msg')
            
            if msg_custom:
                desc = msg_custom.replace("{user}", usuario.name).replace("{reason}", razon)
                title = "Expulsión"
            else:
                title = lang_service.get_text("kick_title", lang)
                desc = lang_service.get_text("kick_desc", lang, user=usuario.name, reason=razon)
            
            await ctx.reply(embed=embed_service.success(title, desc))
        except discord.Forbidden:
            await ctx.reply(embed=embed_service.error("Permisos", lang_service.get_text("error_hierarchy", lang), lite=True), ephemeral=True)
            
    @commands.hybrid_command(name="ban", description="Banea a un miembro.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, usuario: discord.Member, razon: str = "N/A"):
        lang = await lang_service.get_guild_lang(ctx.guild.id)

        if usuario.id == ctx.author.id:
            await ctx.reply(embed=embed_service.warning("!", lang_service.get_text("error_self_action", lang), lite=True), ephemeral=True)
            return

        try:
            await usuario.ban(reason=razon)
            
            # --- OPTIMIZACIÓN: USAR CACHÉ EN LUGAR DE SQL DIRECTO ---
            config = await db_service.get_guild_config(ctx.guild.id)
            msg_custom = config.get('server_ban_msg')
            
            if msg_custom:
                desc = msg_custom.replace("{user}", usuario.name).replace("{reason}", razon)
                title = "Ban"
            else:
                title = lang_service.get_text("ban_title", lang)
                desc = lang_service.get_text("ban_desc", lang, user=usuario.name, reason=razon)

            await ctx.reply(embed=embed_service.success(title, desc))
        except discord.Forbidden:
            await ctx.reply(embed=embed_service.error("Permisos", lang_service.get_text("error_hierarchy", lang), lite=True), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderacion(bot))