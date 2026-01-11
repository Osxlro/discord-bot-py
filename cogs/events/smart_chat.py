import discord
import random
import re
from discord.ext import commands
from services import ai_service, db_service

class SmartChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.random_talk_chance = 0.01 # 1% probabilidad de hablar solo

    async def guardar_mensaje(self, message):
        # Filtramos mensajes muy cortos o comandos
        if len(message.content) > 2 and not message.content.startswith(("/", "!")):
            await db_service.execute(
                "INSERT INTO chat_logs (guild_id, user_name, content) VALUES (?, ?, ?)",
                (message.guild.id, message.author.name, message.content)
            )

    async def obtener_contexto(self, guild_id):
        rows = await db_service.fetch_all(
            "SELECT user_name, content FROM chat_logs WHERE guild_id = ? ORDER BY id DESC LIMIT 10",
            (guild_id,)
        )
        return "\n".join([f"{r['user_name']}: {r['content']}" for r in reversed(rows)])

    async def obtener_lore(self, guild_id):
        rows = await db_service.fetch_all(
            "SELECT user_name, content FROM chat_logs WHERE guild_id = ? ORDER BY RANDOM() LIMIT 2",
            (guild_id,)
        )
        return "\n".join([f"[{r['user_name']} dijo]: {r['content']}" for r in rows])

    async def investigar_db(self, guild_id, termino):
        # Búsqueda SQL rápida
        rows = await db_service.fetch_all(
            "SELECT user_name, content, timestamp FROM chat_logs WHERE guild_id = ? AND content LIKE ? ORDER BY id DESC LIMIT 5",
            (guild_id, f"%{termino}%")
        )
        if not rows: return "No encontré nada relevante."
        return "\n".join([f"[{r['timestamp']}] {r['user_name']}: {r['content']}" for r in rows])

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return

        # 1. Guardar siempre (Memoria a largo plazo)
        await self.guardar_mensaje(message)

        # 2. Decidir si hablar
        es_mencion = self.bot.user in message.mentions
        es_reply = (message.reference and message.reference.resolved and 
                    message.reference.resolved.author.id == self.bot.user.id)
        hablar_random = random.random() < self.random_talk_chance

        if es_mencion or es_reply or hablar_random:
            async with message.channel.typing():
                contexto = await self.obtener_contexto(message.guild.id)
                lore = await self.obtener_lore(message.guild.id)
                
                respuesta = await ai_service.generar_respuesta(message.content, contexto, lore)

        # Detectar [INVESTIGAR: "algo"] con Regex seguro
        match = re.search(r"\[INVESTIGAR:\s*[\"']?([^\"']+)[\"']?\]", respuesta)
        
        if match:
            try:
                termino = match.group(1) # Captura lo que está adentro
                
                # Buscar en BD
                evidencia = await self.investigar_db(message.guild.id, termino)
                
                nuevo_prompt = f"""
                El usuario dijo: "{message.content}"
                Pediste investigar "{termino}".

                RESULTADOS DE LA BASE DE DATOS:
                {evidencia}

                Ahora responde usando esta info.
                """
                respuesta_final = await ai_service.generar_respuesta(nuevo_prompt, contexto, lore)
                await message.reply(respuesta_final)
                
            except Exception as e:
                print(f"Error investigando: {e}")
                await message.reply("Me dio un ictus intentando recordar...")
        else:
            # Si no hay investigación, responde normal
            await message.reply(respuesta)

async def setup(bot: commands.Bot):
    await bot.add_cog(SmartChat(bot))