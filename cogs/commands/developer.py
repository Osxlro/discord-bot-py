import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services import db_service, embed_service, lang_service, pagination_service

logger = logging.getLogger(__name__)

class StatusSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Selecciona un estado para eliminar...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        status_id = int(self.values[0])
        await db_service.execute("DELETE FROM bot_statuses WHERE id = ?", (status_id,))
        logger.info(f"Status eliminado (ID: {status_id}) por {interaction.user}")
        await interaction.response.edit_message(
            embed=embed_service.success("Status", "🗑️ Estado eliminado de la lista."), 
            view=None
        )

class StatusDeleteView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=60)
        self.add_item(StatusSelect(options))

class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="status", description="Gestiona los estados rotativos del bot.")
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    async def status_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @status_group.command(name="listar", description="Muestra la lista de estados configurados.")
    async def listar(self, ctx: commands.Context):
        # Listado solo para el admin (EPHEMERAL)
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        rows = await db_service.fetch_all("SELECT type, text FROM bot_statuses")
        
        if not rows:
            return await ctx.send(embed=embed_service.warning("Status", lang_service.get_text("status_empty", lang)), ephemeral=True)
        
        desc = lang_service.get_text("status_list_desc", lang) + "\n\n"
        for i, row in enumerate(rows, 1):
            desc += f"`{i}.` **[{row['type'].title()}]** {row['text']}\n"
            
        title = lang_service.get_text("status_list_title", lang)
        await ctx.send(embed=embed_service.info(title, desc), ephemeral=True)

    @status_group.command(name="agregar", description="Añade un nuevo estado a la rotación.")
    @app_commands.describe(tipo="Actividad", texto="Lo que se mostrará")
    async def agregar(self, ctx: commands.Context, tipo: Literal["playing", "watching", "listening", "competing"], texto: str):
        await db_service.execute("INSERT INTO bot_statuses (type, text) VALUES (?, ?)", (tipo, texto))
        logger.info(f"Status agregado: [{tipo}] {texto} por {ctx.author}")
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        msg = lang_service.get_text("status_add", lang, text=texto, type=tipo)

        await ctx.send(embed=embed_service.success("Status Guardado", msg), ephemeral=True)

    @status_group.command(name="eliminar", description="Elimina un estado seleccionándolo de la lista.")
    async def eliminar(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        # Optimización: Traer solo los últimos 25 registros en lugar de toda la tabla
        rows = await db_service.fetch_all("SELECT id, type, text FROM bot_statuses ORDER BY id DESC LIMIT 25")
        
        if not rows:
            return await ctx.send(embed=embed_service.warning("Status", lang_service.get_text("status_empty", lang)), ephemeral=True)

        options = []
        for row in rows:
            label = f"[{row['type'].title()}] {row['text']}"
            if len(label) > 100: label = label[:97] + "..."
            options.append(discord.SelectOption(label=label, value=str(row['id']), emoji="🔸"))

        view = StatusDeleteView(options)
        ph = lang_service.get_text("status_placeholder", lang)
        
        await ctx.send(f"👇 **{ph}**", view=view, ephemeral=True)

    @commands.hybrid_command(name="listservers", description="Lista los servidores conectados (Solo Owner).", hidden=True)
    @commands.is_owner()
    async def listservers(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        
        if not guilds:
            return await ctx.send(embed=embed_service.warning("Info", "No estoy en ningún servidor."), ephemeral=True)

        pages = []
        chunk_size = 10
        chunks = [guilds[i:i + chunk_size] for i in range(0, len(guilds), chunk_size)]

        for i, chunk in enumerate(chunks):
            desc = ""
            for guild in chunk:
                desc += f"**{guild.name}**\n🆔 `{guild.id}` | 👥 **{guild.member_count}** | 👑 <@{guild.owner_id}>\n\n"
            
            embed = discord.Embed(title=f"📊 Servidores ({len(self.bot.guilds)})", description=desc, color=discord.Color.gold())
            embed.set_footer(text=f"Página {i+1}/{len(chunks)}")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0], ephemeral=True)
        else:
            view = pagination_service.Paginator(pages, ctx.author.id)
            await ctx.send(embed=pages[0], view=view, ephemeral=True)

    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        # Sync sigue siendo público o privado según prefieras, pero como es owner-only da igual.
        msg = await ctx.send("🔄 Sincronizando...")
        try:
            synced = await self.bot.tree.sync()
            await msg.edit(content=f"✅ **{len(synced)}** comandos sincronizados.")
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(Developer(bot))