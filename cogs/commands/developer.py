import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from services import db_service, embed_service, lang_service

# --- VISTAS (MENÚ DESPLEGABLE) ---
class StatusSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Selecciona un estado para eliminar...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # El valor es el ID en string
        status_id = int(self.values[0])
        
        # Eliminar de DB
        await db_service.execute("DELETE FROM bot_statuses WHERE id = ?", (status_id,))
        
        # Feedback visual
        await interaction.response.edit_message(
            embed=embed_service.success("Status", "🗑️ Estado eliminado de la lista."), 
            view=None # Quitamos el menú
        )

class StatusDeleteView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=60)
        self.add_item(StatusSelect(options))

# --- COG PRINCIPAL ---
class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # GRUPO DE COMANDOS /status
    # Permisos: Owner del bot O Administrador del servidor
    @commands.hybrid_group(name="status", description="Gestiona los estados rotativos del bot.")
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    async def status_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    # 1. LISTAR
    @status_group.command(name="listar", description="Muestra la lista de estados configurados.")
    async def listar(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        rows = await db_service.fetch_all("SELECT type, text FROM bot_statuses")
        
        if not rows:
            return await ctx.send(embed=embed_service.warning("Status", lang_service.get_text("status_empty", lang)))
        
        desc = lang_service.get_text("status_list_desc", lang) + "\n\n"
        
        for i, row in enumerate(rows, 1):
            # Ejemplo: 1. [Playing] Minecraft
            desc += f"`{i}.` **[{row['type'].title()}]** {row['text']}\n"
            
        title = lang_service.get_text("status_list_title", lang)
        await ctx.send(embed=embed_service.info(title, desc))

    # 2. AGREGAR
    @status_group.command(name="agregar", description="Añade un nuevo estado a la rotación.")
    @app_commands.describe(tipo="Actividad", texto="Lo que se mostrará")
    async def agregar(self, ctx: commands.Context, tipo: Literal["playing", "watching", "listening", "competing"], texto: str):
        await db_service.execute("INSERT INTO bot_statuses (type, text) VALUES (?, ?)", (tipo, texto))
        
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        msg = lang_service.get_text("status_add", lang, text=texto, type=tipo)
        
        await ctx.send(embed=embed_service.success("Status Guardado", msg))

    # 3. ELIMINAR (Con Menú)
    @status_group.command(name="eliminar", description="Elimina un estado seleccionándolo de la lista.")
    async def eliminar(self, ctx: commands.Context):
        lang = await lang_service.get_guild_lang(ctx.guild.id)
        rows = await db_service.fetch_all("SELECT id, type, text FROM bot_statuses")
        
        if not rows:
            return await ctx.send(embed=embed_service.warning("Status", lang_service.get_text("status_empty", lang)))

        # Preparamos las opciones del menú (Max 25 por límite de Discord)
        options = []
        for row in rows[-25:]:
            label = f"[{row['type'].title()}] {row['text']}"
            # Recortamos si es muy largo para que no de error
            if len(label) > 100: label = label[:97] + "..."
            
            options.append(discord.SelectOption(label=label, value=str(row['id']), emoji="🔸"))

        view = StatusDeleteView(options)
        ph = lang_service.get_text("status_placeholder", lang)
        await ctx.send(f"👇 **{ph}**", view=view)

    # --- OTROS COMANDOS DE DEV ---
    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        """Sincroniza comandos slash manualmente."""
        msg = await ctx.send("🔄 Sincronizando...")
        try:
            synced = await self.bot.tree.sync()
            await msg.edit(content=f"✅ **{len(synced)}** comandos sincronizados.")
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(Developer(bot))