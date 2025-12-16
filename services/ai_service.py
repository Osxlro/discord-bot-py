import os
from google import genai
from google.genai import types
from config import settings

# 1. Configuración del Cliente
API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializamos el cliente (si hay key)
client = None
if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    print("⚠️ ADVERTENCIA: No se encontró GEMINI_API_KEY en .env")

# 2. Prompt del Sistema (Tu personalidad caótica)
SYSTEM_PROMPT = """
Eres un bot de Discord con una personalidad COMPLETAMENTE CAÓTICA, sarcástica, impredecible y divertida.
No eres un asistente servicial aburrido. Eres parte del desmadre del servidor.
Tu memoria funciona leyendo el chat que te pasan.

REGLAS DE ORO:
1. Si el usuario te pregunta algo sobre hechos pasados del servidor ("qué pasó ayer", "quién dijo eso", "de qué hablan", "quién es el admin") y NO tienes esa información en el texto que te acabo de dar:
   Responde ÚNICAMENTE con este formato exacto: [INVESTIGAR: "termino de busqueda"]
   (Ejemplo: [INVESTIGAR: "torneo"], [INVESTIGAR: "pelea ayer"])

2. Si ya tienes la información o es una charla casual, responde con tu personalidad caótica.
3. No uses saludos formales. Sé directo y gracioso.
"""

async def generar_respuesta(prompt_usuario: str, contexto_chat: str = "") -> str:
    """
    Genera una respuesta usando el nuevo SDK de Google Gen AI.
    """
    if not client:
        return "❌ No tengo cerebro (Falta GEMINI_API_KEY)."

    try:
        # Construimos el mensaje final combinando contexto y usuario
        prompt_final = f"""
        CONTEXTO RECIENTE DEL CHAT (Lo que acaba de pasar):
        {contexto_chat}

        USUARIO DICE:
        {prompt_usuario}
        """

        # 3. Llamada Asíncrona (Nueva sintaxis 'client.aio')
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt_final,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.9, # Creatividad alta
                top_p=0.95,
                top_k=64,
                max_output_tokens=1000,
            )
        )
        
        return response.text.strip()

    except Exception as e:
        # Capturamos errores específicos del nuevo SDK o generales
        return f"🔥 Me quemé el cerebro: {str(e)}"