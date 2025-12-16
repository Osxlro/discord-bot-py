import discord
from discord.ext import commands
from services import ai_service

class SmartChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def obtener_historial_reciente(self, channel, limit=15):
        """Memoria a corto plazo: Lo que acaba de pasar."""
        msgs = []
        async for m in channel.history(limit=limit):
            if not m.author.bot:
                msgs.append(f"{m.author.name}: {m.content}")
        return "\n".join(reversed(msgs))

    async def buscar_en_archivos(self, channel, termino_busqueda):
        """
        Memoria a largo plazo: Busca en el pasado (RAG simple).
        Busca en los últimos 300 mensajes algo que coincida.
        """
        hallazgos = []
        contador = 0
        
        # Iteramos hacia atrás
        async for m in channel.history(limit=300):
            if termino_busqueda.lower() in m.content.lower() and not m.author.bot:
                fecha = m.created_at.strftime('%d/%m %H:%M')
                hallazgos.append(f"[{fecha}] {m.author.name}: {m.content}")
                contador += 1
                if contador >= 10: break # Máximo 10 evidencias para no saturar
        
        if not hallazgos:
            return "No encontré nada relevante en los archivos recientes."
        return "\n".join(reversed(hallazgos))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Evitar bucles y bots
        if message.author.bot: return

        # Condiciones para responder:
        # 1. Mención directa (@Bot)
        # 2. Es una respuesta (Reply) a un mensaje del bot
        es_mencion = self.bot.user in message.mentions
        es_reply = (message.reference and message.reference.resolved and 
                    message.reference.resolved.author.id == self.bot.user.id)

        if es_mencion or es_reply:
            async with message.channel.typing():
                # 1. Leemos el contexto inmediato
                contexto = await self.obtener_historial_reciente(message.channel)
                
                # 2. Primer intento de respuesta
                respuesta = await ai_service.generar_respuesta(message.content, contexto)

                # 3. ¿La IA pidió investigar?
                if "[INVESTIGAR:" in respuesta:
                    try:
                        # Extraemos el término entre comillas
                        start = respuesta.find('"') + 1
                        end = respuesta.find('"', start)
                        termino = respuesta[start:end]
                        
                        # Buscamos en el historial profundo
                        evidencia = await self.buscar_en_archivos(message.channel, termino)
                        
                        # 4. Segunda llamada a la IA con la evidencia
                        nuevo_prompt = f"""
                        El usuario preguntó: "{message.content}"
                        
                        No sabías la respuesta, así que busqué en la base de datos y encontré esto:
                        --- INICIO EVIDENCIA ---
                        {evidencia}
                        --- FIN EVIDENCIA ---
                        
                        Ahora sí, responde al usuario basándote en esta evidencia (o búrlate si no hay nada útil).
                        """
                        
                        respuesta_final = await ai_service.generar_respuesta(nuevo_prompt, contexto)
                        await message.reply(respuesta_final)
                        
                    except Exception as e:
                        await message.reply(f"Me tropecé buscando en los archivos... (Error: {e})")
                else:
                    # Respuesta normal
                    await message.reply(respuesta)

async def setup(bot: commands.Bot):
    await bot.add_cog(SmartChat(bot))