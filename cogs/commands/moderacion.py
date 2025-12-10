import discord
from discord.ext import commands
from discord import app_commands
from config import settings
from services import embed_service

class Moderacion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- COMANDO: CLEAR (Limpiar chat) ---
    @commands.hybrid_command(name="clear", description="Borra una cantidad de mensajes del chat")
    @app_commands.describe(cantidad="Número de mensajes a borrar")
    @app_commands.checks.has_permissions(manage_messages=True) # Solo quien pueda gestionar mensajes
    async def clear(self, ctx : commands.Context, cantidad: int):
        
        max_msg = settings.CONFIG.get("moderation_config", {}).get("max_clear_msg", 100)

        if cantidad > max_msg:
            embed = embed_service.error("Demasiados mensajes", f"El límite es borrar {max_msg} mensajes a la vez.")
            await ctx.reply(embed=embed, ephemeral=True)
            return

        # "Pensando..." (importante para operaciones que tardan un poco)
        await ctx.defer(ephemeral=True) 

        # Ejecutamos la limpieza
        deleted = await ctx.channel.purge(limit=cantidad)
        
        embed = embed_service.success(
            title="Limpieza Completada", 
            description=f"Se han eliminado **{len(deleted)}** mensajes."
        )
        # Usamos followup porque ya usamos defer
        await ctx.send(embed=embed)

    # --- COMANDO: KICK (Expulsar) ---
    @commands.hybrid_command(name="kick", description="Expulsa a un miembro del servidor")
    @app_commands.describe(usuario="El usuario a expulsar", razon="Motivo de la expulsión")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, usuario: discord.Member, razon: str = "Sin razón especificada"):
        
        # Evitar autokick o kick al bot
        if usuario.id == ctx.author.id:
            await ctx.reply("No puedes expulsarte a ti mismo.", ephemeral=True)
            return
            
        try:
            # Intentamos enviar MD al usuario antes de expulsarlo
            try:
                embed_md = embed_service.error("Has sido expulsado", f"Servidor: {ctx.guild}\nRazón: {razon}")
                await usuario.send(embed=embed_md)
            except:
                pass # Si tiene MD cerrados, no pasa nada

            # Acción real
            await usuario.kick(reason=razon)

            # Confirmación en el chat
            embed = embed_service.success("Martillo de la Justicia", f"**{usuario.name}** ha sido expulsado.\n📝 Razón: {razon}")
            await ctx.reply(embed=embed)

        except discord.Forbidden:
            embed = embed_service.error("Error de Jerarquía", "No puedo expulsar a este usuario (tal vez tiene un rol superior al mío).")
            await ctx.reply(embed=embed, ephemeral=True)

    # --- COMANDO: BAN (Banear) ---
    @commands.hybrid_command(name="ban", description="Banea a un miembro permanentemente")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, usuario: discord.Member, razon: str = "Sin razón especificada"):
        
        if usuario.id == ctx.author.id:
            await ctx.reply("No puedes banearte a ti mismo.", ephemeral=True)
            return

        try:
            # Acción real
            await usuario.ban(reason=razon)

            embed = embed_service.success("Usuario Baneado", f"**{usuario.name}** ha sido baneado.\n📝 Razón: {razon}")
            await ctx.reply(embed=embed)

        except discord.Forbidden:
            embed = embed_service.error("Error de Jerarquía", "No puedo banear a este usuario (rol superior al mío).")
            await ctx.reply(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderacion(bot))