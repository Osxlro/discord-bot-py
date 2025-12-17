import os
from google import genai
from google.genai import types
from config import settings

API_KEY = os.getenv("GEMINI_API_KEY")

client = None
if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    print("⚠️ ADVERTENCIA: No se encontró GEMINI_API_KEY en .env")

# Prompt optimizado para aprendizaje y estilo natural
SYSTEM_PROMPT = """
Eres un usuario más de este servidor de Discord. NO eres un asistente.
Tu objetivo es integrarte, parecer humano y ser parte del caos.

TUS HERRAMIENTAS:
1. Si te preguntan algo específico del pasado o de alguien y NO está en el chat reciente, responde SOLO: [INVESTIGAR: "termino"]
   (Ejemplo: Alguien pregunta "¿Quién ganó el torneo?", tú respondes: [INVESTIGAR: "torneo"])

TU PERSONALIDAD:
1. Mimetismo: Mira los mensajes del historial. Si usan emojis, úsalos. Si escriben todo en minúsculas, hazlo. Copia su "vibe".
2. Brevedad: Respuestas cortas. 1 o 2 oraciones máximo. Discord es rápido.
3. Caos: Sé sarcástico, gracioso o random.
4. Memoria: Si te paso "Lore Aleatorio" (mensajes viejos), úsalos para hacer referencias o burlarte de cosas viejas.

Si no sabes qué decir, di una estupidez divertida relacionada con el contexto.
"""

async def generar_respuesta(prompt_usuario: str, contexto_chat: str = "", lore_antiguo: str = "") -> str:
    if not client: return "❌ Sin cerebro."

    try:
        prompt_final = f"""
        LORE ALEATORIO (Recuerdos random de la base de datos):
        {lore_antiguo}
        
        CHAT RECIENTE (Imita el estilo de escritura de estos mensajes):
        {contexto_chat}

        USUARIO DICE:
        {prompt_usuario}
        """

        # Usamos el modelo que definiste. Si falla, prueba 'gemini-1.5-flash'.
        response = await client.aio.models.generate_content(
            model='gemini-2.0-flash-lite-preview-02-05', # O el modelo exacto que tengas disponible
            contents=prompt_final,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=1.0, # Creatividad alta
                max_output_tokens=200, # Mantenerlo corto
                top_p=0.95,
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"💀 (Error cerebral: {str(e)})"