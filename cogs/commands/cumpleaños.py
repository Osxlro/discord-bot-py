import discord
from discord.ext import commands, tasks
from typing import Literal
from services import db_service, embed_service, lang_service
import datetime
from config import settings

class Cumpleanos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    @tasks.loop(hours=settings.BIRTHDAY_CONFIG["CHECK_INTERVAL_HOURS"])
    async def check_birthdays(self):
        await self.bot.wait_until_ready()
        hoy = datetime.date.today()
        fecha_str = f"{hoy.day}/{hoy.month}"
        
        users = await db_service.fetch_all("SELECT user_id, personal_birthday_msg FROM users WHERE birthday = ? AND celebrate = 1", (fecha_str,))
        if not users: return

        for guild in self.bot.guilds:
            lang = await lang_service.get_guild_lang(guild.id)
            config = await db_service.fetch_one("SELECT birthday_channel_id, server_birthday_msg FROM guild_config WHERE guild_id = ?", (guild.id,))
            if not config or not config['birthday_channel_id']: continue
            
            channel = guild.get_channel(config['birthday_channel_id'])
            if not channel: continue

            genericos = []
            for row in users:
                member = guild.get_member(row['user_id'])
                if not member: continue

                if row['personal_birthday_msg']:
                    msg = row['personal_birthday_msg'].replace("{user}", member.mention)
                    title = lang_service.get_text("bday_title", lang)
                    await channel.send(content=member.mention, embed=embed_service.success(title, msg, thumbnail=member.display_avatar.url))
                else:
                    genericos.append(member.mention)

            if genericos:
                msg_base = config['server_birthday_msg'] or lang_service.get_text("bday_server_default", lang)
                msg_final = msg_base.replace("{users}", ", ".join(genericos)).replace("{user}", ", ".join(genericos))
                title = lang_service.get_text("bday_title", lang)
                await channel.send(embed=embed_service.success(title, msg_final, thumbnail=settings.BIRTHDAY_CONFIG["CAKE_ICON"]))

    @commands.hybrid_group(name="cumple")
    async def cumple(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None: await ctx.send_help(ctx.command)

    @cumple.command(name="establecer", description="Establece tu cumpleaños.")
    async def establecer(self, ctx: commands.Context, dia: int, mes: int):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        try:
            datetime.date(2000, mes, dia)
            fecha = f"{dia}/{mes}"
            await db_service.execute("INSERT OR REPLACE INTO users (user_id, birthday, celebrate) VALUES (?, ?, 1)", (ctx.author.id, fecha))
            msg = lang_service.get_text("bday_saved", lang, date=fecha)
            await ctx.reply(embed=embed_service.success(lang_service.get_text("title_success", lang), msg))
        except ValueError:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("bday_invalid", lang)), ephemeral=True)

    @cumple.command(name="eliminar", description= "Elimina tu cumpleaños, o el de alguien más.")
    async def eliminar(self, ctx: commands.Context, usuario: discord.Member = None):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        target = usuario or ctx.author
        if target.id != ctx.author.id and not ctx.author.guild_permissions.administrator:
            await ctx.reply(embed=embed_service.error(lang_service.get_text("title_error", lang), lang_service.get_text("error_no_perms", lang)), ephemeral=True)
            return

        await db_service.execute("UPDATE users SET birthday = NULL WHERE user_id = ?", (target.id,))
        await ctx.reply(embed=embed_service.success(lang_service.get_text("title_success", lang), lang_service.get_text("bday_removed", lang)))

    @cumple.command(name="privacidad", description="Decide si festejar tu cumpleaños o no.")
    async def privacidad(self, ctx: commands.Context, estado: Literal["Visible", "Oculto"]):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        val = 1 if estado == "Visible" else 0
        await db_service.execute("UPDATE users SET celebrate = ? WHERE user_id = ?", (val, ctx.author.id))
        msg = lang_service.get_text("bday_visible" if val else "bday_hidden", lang)
        await ctx.reply(embed=embed_service.success(lang_service.get_text("bday_privacy", lang), msg))

    @cumple.command(name="lista", description="Revisa la lista de proximos cumpleaños.")
    async def lista(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        rows = await db_service.fetch_all("SELECT user_id, birthday FROM users WHERE birthday IS NOT NULL AND celebrate = 1")
        
        lista = []
        hoy = datetime.date.today()
        for row in rows:
            try:
                d, m = map(int, row['birthday'].split('/'))
                bday = datetime.date(hoy.year, m, d)
                if bday < hoy: bday = datetime.date(hoy.year + 1, m, d)
                diff = (bday - hoy).days
                lista.append((diff, row['user_id'], row['birthday']))
            except: continue
        
        lista.sort(key=lambda x: x[0])
        txt = ""
        for dias, uid, fecha in lista[:settings.BIRTHDAY_CONFIG["LIST_LIMIT"]]:
            user = ctx.guild.get_member(uid)
            if user:
                key = "bday_today" if dias == 0 else "bday_soon"
                txt += lang_service.get_text(key, lang, user=user.display_name, date=fecha, days=dias) + "\n"

        await ctx.reply(embed=embed_service.info(lang_service.get_text("bday_list_title", lang), txt or lang_service.get_text("bday_list_empty", lang)))

async def setup(bot: commands.Bot):
    await bot.add_cog(Cumpleanos(bot))