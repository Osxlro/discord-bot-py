import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Literal
from services import db_service, embed_service
import datetime

class Cumpleanos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.cancel()

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        await self.bot.wait_until_ready()
        
        hoy = datetime.date.today()
        fecha_hoy_str = f"{hoy.day}/{hoy.month}"
        
        # Buscar usuarios que cumplen hoy y quieren celebrar
        # Obtenemos también su mensaje personalizado si existe
        cumpleaneros = await db_service.fetch_all(
            "SELECT user_id, personal_birthday_msg FROM users WHERE birthday = ? AND celebrate = 1", 
            (fecha_hoy_str,)
        )
        
        if not cumpleaneros:
            return

        for guild in self.bot.guilds:
            # 1. Configuración del Servidor
            config = await db_service.fetch_one("SELECT birthday_channel_id, server_birthday_msg FROM guild_config WHERE guild_id = ?", (guild.id,))
            
            if not config or not config['birthday_channel_id']:
                continue 
            
            channel = guild.get_channel(config['birthday_channel_id'])
            if not channel:
                continue

            # Mensaje Base del Servidor
            msg_server_raw = config['server_birthday_msg'] or "Hoy es un día especial. Queremos desearle un muy feliz cumpleaños a:\n\n✨ {user} ✨\n\n¡Que pases un día increíble!"

            # 2. Clasificar Usuarios
            usuarios_genericos = [] # Usarán el mensaje del servidor
            
            for row in cumpleaneros:
                member = guild.get_member(row['user_id'])
                if not member: 
                    continue # El usuario no está en este servidor

                # Si tiene mensaje PERSONALIZADO, enviamos uno individual
                if row['personal_birthday_msg']:
                    msg_personal = row['personal_birthday_msg'].replace("{user}", member.mention)
                    embed_p = embed_service.success("🎉 ¡Feliz Cumpleaños! 🎂", msg_personal)
                    embed_p.set_thumbnail(url=member.display_avatar.url)
                    await channel.send(content=member.mention, embed=embed_p)
                else:
                    # Si no, va al grupo
                    usuarios_genericos.append(member.mention)

            # 3. Enviar mensaje GRUPAL (si hay)
            if usuarios_genericos:
                lista_menciones = ", ".join(usuarios_genericos)
                # Reemplazamos {user} por la lista de todos
                msg_final = msg_server_raw.replace("{user}", lista_menciones)
                
                embed_g = embed_service.success("🎉 ¡Feliz Cumpleaños! 🎂", msg_final)
                embed_g.set_thumbnail(url="https://emojigraph.org/media/apple/birthday-cake_1f382.png")
                await channel.send(embed=embed_g)

    # --- COMANDOS EXISTENTES ---
    @commands.hybrid_group(name="cumple", description="Sistema de cumpleaños")
    async def cumple(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @cumple.command(name="establecer", description="Guarda tu fecha de cumpleaños")
    @app_commands.describe(dia="Día (1-31)", mes="Mes (1-12)")
    async def establecer(self, ctx: commands.Context, dia: int, mes: int):
        try:
            datetime.date(2000, mes, dia)
            fecha_str = f"{dia}/{mes}"
        except ValueError:
            await ctx.reply(embed=embed_service.error("Fecha Inválida", "Esa fecha no existe."), ephemeral=True)
            return

        await db_service.execute(
            "INSERT OR REPLACE INTO users (user_id, birthday, celebrate) VALUES (?, ?, 1)",
            (ctx.author.id, fecha_str)
        )
        await ctx.reply(embed=embed_service.success("¡Fecha Guardada!", f"Cumpleaños: **{fecha_str}** 🎂"))

    @cumple.command(name="eliminar", description="Borra un cumpleaños")
    async def eliminar(self, ctx: commands.Context, usuario: discord.Member = None):
        target = usuario or ctx.author
        es_admin = ctx.author.guild_permissions.administrator
        if target.id != ctx.author.id and not es_admin:
            await ctx.reply(embed=embed_service.error("Sin Permisos", "Solo puedes borrar el tuyo."), ephemeral=True)
            return

        await db_service.execute("UPDATE users SET birthday = NULL WHERE user_id = ?", (target.id,))
        await ctx.reply(embed=embed_service.success("Eliminado", f"Cumpleaños de {target.name} borrado."))

    @cumple.command(name="privacidad", description="Configura si quieres que se anuncie tu cumpleaños")
    async def privacidad(self, ctx: commands.Context, estado: Literal["Visible (Anunciar)", "Oculto (Privado)"]):
        nuevo_valor = 1 if estado == "Visible (Anunciar)" else 0
        await db_service.execute("UPDATE users SET celebrate = ? WHERE user_id = ?", (nuevo_valor, ctx.author.id))
        msg = "✅ **Visible**" if nuevo_valor else "🔕 **Oculto**"
        await ctx.reply(embed=embed_service.success("Configuración Actualizada", msg))

    @cumple.command(name="lista", description="Muestra los próximos cumpleaños")
    async def lista(self, ctx: commands.Context):
        rows = await db_service.fetch_all("SELECT user_id, birthday FROM users WHERE birthday IS NOT NULL AND celebrate = 1")
        if not rows:
            await ctx.reply(embed=embed_service.info("Vacío", "No hay cumpleaños registrados."))
            return

        lista_cumples = []
        hoy = datetime.date.today()

        for row in rows:
            uid, fecha_str = row['user_id'], row['birthday']
            try:
                dia, mes = map(int, fecha_str.split('/'))
                cumple_este_ano = datetime.date(hoy.year, mes, dia)
                if cumple_este_ano < hoy:
                    proximo = datetime.date(hoy.year + 1, mes, dia)
                else:
                    proximo = cumple_este_ano
                dias_restantes = (proximo - hoy).days
                lista_cumples.append((dias_restantes, uid, fecha_str))
            except: continue 

        lista_cumples.sort(key=lambda x: x[0])
        top_10 = lista_cumples[:10]
        
        texto = ""
        for dias, uid, fecha in top_10:
            usuario = ctx.guild.get_member(uid)
            if usuario:
                nombre = usuario.display_name
                if dias == 0: texto += f"🎂 **¡HOY!** - {nombre} \n"
                else: texto += f"📅 `{fecha}` - **{nombre}** (en {dias} días)\n"

        await ctx.reply(embed=embed_service.info("Próximos Cumpleaños 🍰", texto or "No pude encontrar usuarios activos."))

async def setup(bot: commands.Bot):
    await bot.add_cog(Cumpleanos(bot))