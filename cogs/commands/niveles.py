import logging
import random
import discord
from discord.ext import commands
from config import settings
from services import db_service, embed_service, lang_service, pagination_service

logger = logging.getLogger(__name__)

class Niveles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(
            1, 
            settings.XP_CONFIG["COOLDOWN"], 
            commands.BucketType.user
        )

    def get_ratelimit(self, message: discord.Message):
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        
        # Evitar dar XP por comandos para prevenir el spam de niveles.
        prefix = await self.bot.get_prefix(message)
        if isinstance(prefix, list) and any(message.content.startswith(p) for p in prefix): return
        if isinstance(prefix, str) and message.content.startswith(prefix): return

        # Sistema de Cooldown para evitar el farmeo rápido de XP.
        if self.get_ratelimit(message): return
        xp_ganada = random.randint(
            settings.XP_CONFIG["MIN_XP"], 
            settings.XP_CONFIG["MAX_XP"]
        )
        
        nuevo_nivel, subio_de_nivel = await db_service.add_xp(message.guild.id, message.author.id, xp_ganada)
        
        if subio_de_nivel:
            await self._enviar_mensaje_nivel(message, nuevo_nivel)

    async def _enviar_mensaje_nivel(self, message: discord.Message, nuevo_nivel: int):
        try:
            lang = await lang_service.get_guild_lang(message.guild.id)
            user_conf = await db_service.fetch_one("SELECT personal_level_msg FROM users WHERE user_id = ?", (message.author.id,))
            guild_conf = await db_service.get_guild_config(message.guild.id)
            
            msg_raw = None
            if user_conf and user_conf['personal_level_msg']:
                msg_raw = user_conf['personal_level_msg']
            elif guild_conf.get('server_level_msg'):
                msg_raw = guild_conf['server_level_msg']
            else:
                msg_raw = lang_service.get_text("level_up_default", lang)
            
            msg_final = msg_raw.replace("{user}", message.author.mention)\
                               .replace("{level}", str(nuevo_nivel))\
                               .replace("{server}", message.guild.name)
            
            await message.channel.send(msg_final)
        except Exception as e:
            logger.error(f"Error enviando nivel: {e}")

    @commands.hybrid_command(name="leaderboard", description="Muestra el top de XP del servidor")
    async def leaderboard(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        rows = await db_service.fetch_all(
            "SELECT user_id, level, xp, rebirths FROM guild_stats WHERE guild_id = ? ORDER BY rebirths DESC, level DESC, xp DESC LIMIT 50", 
            (ctx.guild.id,)
        )
        
        if not rows:
            msg = lang_service.get_text("leaderboard_empty", lang)
            await ctx.reply(embed=embed_service.info("Vacío", msg))
            return

        chunk_size = 10
        chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
        pages = []

        title = lang_service.get_text("leaderboard_title", lang, server=ctx.guild.name)

        for i, chunk in enumerate(chunks):
            lines = []
            start_rank = (i * chunk_size) + 1
            
            for j, row in enumerate(chunk, start=start_rank):
                user_id = row['user_id']
                member = ctx.guild.get_member(user_id)
                
                # Escapamos nombres para evitar roturas de formato visual
                name = discord.utils.escape_markdown(member.display_name) if member else f"Usuario {user_id}"
                
                rebirth_text = f"🌀 {row['rebirths']} | " if row['rebirths'] > 0 else ""
                xp_fmt = f"{row['xp']:,}" # Formato con comas (ej: 1,200)
                
                if j == 1:
                    lines.append(f"🥇 **{name}**\n> 👑 {rebirth_text}Nvl **{row['level']}** • ✨ `{xp_fmt}` XP")
                elif j == 2:
                    lines.append(f"🥈 **{name}**\n> 🛡️ {rebirth_text}Nvl **{row['level']}** • ✨ `{xp_fmt}` XP")
                elif j == 3:
                    lines.append(f"🥉 **{name}**\n> ⚔️ {rebirth_text}Nvl **{row['level']}** • ✨ `{xp_fmt}` XP")
                else:
                    lines.append(f"`#{j}` **{name}** • {rebirth_text}Nvl {row['level']} • `{xp_fmt}` XP")
            
            desc = "\n\n".join(lines)
            embed = embed_service.info(title, desc, thumbnail=ctx.guild.icon.url if ctx.guild.icon else None)
            embed.set_footer(text=f"Página {i+1}/{len(chunks)}")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.reply(embed=pages[0])
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            await ctx.reply(embed=pages[0], view=view)

    @commands.hybrid_command(name="rebirth", description="Reinicia tu nivel (requiere Nivel 100) para ganar un Rebirth.")
    async def rebirth(self, ctx: commands.Context):
        await ctx.defer()
        success, result = await db_service.do_rebirth(ctx.guild.id, ctx.author.id)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        
        if success:
            msg = lang_service.get_text("rebirth_success", lang, rebirths=result)
            await ctx.send(embed=embed_service.success("🌀 Rebirth Exitoso", msg))
        else:
            if result == "no_data":
                msg = lang_service.get_text("rank_no_data", lang)
            elif isinstance(result, int):
                msg = lang_service.get_text("rebirth_fail_level", lang, level=result)
            else:
                msg = lang_service.get_text("rebirth_fail_generic", lang)
            
            await ctx.send(embed=embed_service.error("Rebirth Fallido", msg))

async def setup(bot: commands.Bot):
    await bot.add_cog(Niveles(bot))