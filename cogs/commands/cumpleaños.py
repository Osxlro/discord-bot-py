import discord
from discord.ext import commands, tasks # Importamos tasks
from discord import app_commands
from typing import Literal
from services import db_service, embed_service
import datetime
import asyncio

class Cumpleanos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_birthdays.start() # Iniciamos el loop al cargar el Cog

    def cog_unload(self):
        self.check_birthdays.cancel() # Lo detenemos si se descarga

    # --- TAREA AUTOMÁTICA ---
    @tasks.loop(hours=24) # Revisa una vez al día
    async def check_birthdays(self):
        # Esperar a que el bot esté listo
        await self.bot.wait_until_ready()
        
        # 1. Obtener fecha de hoy (dia/mes)
        hoy = datetime.date.today()
        fecha_hoy_str = f"{hoy.day}/{hoy.month}"
        
        # 2. Buscar cumpleañeros en la DB que quieran celebrar
        cumpleaneros = await db_service.fetch_all(
            "SELECT user_id FROM users WHERE birthday = ? AND celebrate = 1", 
            (fecha_hoy_str,)
        )
        
        if not cumpleaneros:
            return # Nadie cumple hoy

        # 3. Agrupar cumpleañeros por Servidor para no spamear consultas
        # (Esta lógica es sencilla: iteramos por servidor donde esté el bot)
        for guild in self.bot.guilds:
            # Obtener canal de cumples de este servidor
            config = await db_service.fetch_one("SELECT birthday_channel_id FROM guild_config WHERE guild_id = ?", (guild.id,))
            
            if not config or not config['birthday_channel_id']:
                continue # Este server no tiene canal configurado
            
            channel = guild.get_channel(config['birthday_channel_id'])
            if not channel:
                continue

            # Verificamos cuáles de los cumpleañeros están en ESTE servidor
            usuarios_a_felicitar = []
            for row in cumpleaneros:
                member = guild.get_member(row['user_id'])
                if member:
                    usuarios_a_felicitar.append(member.mention)
            
            if usuarios_a_felicitar:
                # 4. Enviar felicitación
                lista_menciones = ", ".join(usuarios_a_felicitar)
                embed = embed_service.success(
                    "🎉 ¡Feliz Cumpleaños! 🎂", 
                    f"Hoy es un día especial. Queremos desearle un muy feliz cumpleaños a:\n\n✨ {lista_menciones} ✨\n\n¡Que pasen un día increíble!"
                )
                embed.set_thumbnail(url="https://emojigraph.org/media/apple/birthday-cake_1f382.png") # Imagen genérica de pastel
                await channel.send(embed=embed)

    # --- (AQUÍ ABAJO VAN LOS COMANDOS QUE YA TENÍAS: establecer, eliminar, privacidad, lista) ---
    # COPIA Y PEGA TUS COMANDOS EXISTENTES AQUÍ
    # ...
    
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