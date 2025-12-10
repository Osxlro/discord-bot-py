import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from services import db_service, embed_service
import datetime

class Cumpleanos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="cumple", description="Sistema de cumpleaños")
    async def cumple(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    # --- 1. ESTABLECER ---
    @cumple.command(name="establecer", description="Guarda tu fecha de cumpleaños")
    @app_commands.describe(dia="Día (1-31)", mes="Mes (1-12)")
    async def establecer(self, ctx: commands.Context, dia: int, mes: int):
        try:
            # Validar fecha real
            datetime.date(2000, mes, dia)
            fecha_str = f"{dia}/{mes}"
        except ValueError:
            await ctx.reply(embed=embed_service.error("Fecha Inválida", "Esa fecha no existe en el calendario."), ephemeral=True)
            return

        # Guardamos fecha y activamos la celebración por defecto (celebrate=1)
        await db_service.execute(
            "INSERT OR REPLACE INTO users (user_id, birthday, celebrate) VALUES (?, ?, 1)",
            (ctx.author.id, fecha_str)
        )

        embed = embed_service.success(
            "¡Fecha Guardada!", 
            f"He guardado tu cumpleaños el día: **{fecha_str}** 🎂\nSe anunciará automáticamente."
        )
        await ctx.reply(embed=embed)

    # --- 2. ELIMINAR (Con seguridad) ---
    @cumple.command(name="eliminar", description="Borra un cumpleaños (El tuyo o el de otro si eres Admin)")
    async def eliminar(self, ctx: commands.Context, usuario: discord.Member = None):
        target = usuario or ctx.author
        
        # Verificación de permisos
        es_admin = ctx.author.guild_permissions.administrator
        if target.id != ctx.author.id and not es_admin:
            await ctx.reply(embed=embed_service.error("Sin Permisos", "Solo puedes borrar tu propio cumpleaños."), ephemeral=True)
            return

        # Borramos estableciendo NULL en la DB
        await db_service.execute("UPDATE users SET birthday = NULL WHERE user_id = ?", (target.id,))
        
        msg = "Tu cumpleaños ha sido eliminado." if target == ctx.author else f"El cumpleaños de **{target.name}** ha sido eliminado."
        await ctx.reply(embed=embed_service.success("Eliminado", msg))

    # --- 3. PRIVACIDAD (Unificado) ---
    @cumple.command(name="privacidad", description="Configura si quieres que se anuncie tu cumpleaños")
    @app_commands.describe(estado="Elige si quieres que celebremos tu día")
    async def privacidad(self, ctx: commands.Context, estado: Literal["Visible (Anunciar)", "Oculto (Privado)"]):
        
        # Convertimos la elección de texto a booleano (1 o 0)
        nuevo_valor = 1 if estado == "Visible (Anunciar)" else 0
        
        # Actualizamos la base de datos
        await db_service.execute("UPDATE users SET celebrate = ? WHERE user_id = ?", (nuevo_valor, ctx.author.id))
        
        if nuevo_valor == 1:
            msg = "✅ **Visible:** Ahora todos sabrán cuando es tu cumpleaños."
        else:
            msg = "🔕 **Oculto:** Tu cumpleaños será secreto y no se anunciará."
            
        await ctx.reply(embed=embed_service.success("Configuración Actualizada", msg))

    # --- 4. LISTA (Mostrar próximos) ---
    @cumple.command(name="lista", description="Muestra los próximos cumpleaños del servidor")
    async def lista(self, ctx: commands.Context):
        # Obtenemos usuarios que tengan cumple y quieran celebrarlo
        rows = await db_service.fetch_all("SELECT user_id, birthday FROM users WHERE birthday IS NOT NULL AND celebrate = 1")
        
        if not rows:
            await ctx.reply(embed=embed_service.info("Vacío", "No hay cumpleaños registrados (o públicos) aún."))
            return

        lista_cumples = []
        hoy = datetime.date.today()

        for row in rows:
            uid, fecha_str = row['user_id'], row['birthday']
            try:
                dia, mes = map(int, fecha_str.split('/'))
                
                # Calcular próxima fecha
                cumple_este_ano = datetime.date(hoy.year, mes, dia)
                if cumple_este_ano < hoy:
                    proximo = datetime.date(hoy.year + 1, mes, dia)
                else:
                    proximo = cumple_este_ano
                
                dias_restantes = (proximo - hoy).days
                lista_cumples.append((dias_restantes, uid, fecha_str))
            except:
                continue 

        # Ordenar por los que faltan menos días y tomar top 10
        lista_cumples.sort(key=lambda x: x[0])
        top_10 = lista_cumples[:10]
        
        texto = ""
        for dias, uid, fecha in top_10:
            usuario = ctx.guild.get_member(uid)
            nombre = usuario.display_name if usuario else "Usuario Desconocido"
            
            if dias == 0:
                texto += f"🎂 **¡HOY!** - {nombre} \n"
            else:
                texto += f"📅 `{fecha}` - **{nombre}** (en {dias} días)\n"

        embed = embed_service.info("Próximos Cumpleaños 🍰", texto or "No pude encontrar usuarios activos.")
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Cumpleanos(bot))