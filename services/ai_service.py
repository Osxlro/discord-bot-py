import os
from google import genai
from google.genai import types
from config import settings

API_KEY = os.getenv("GEMINI_API_KEY")

client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"❌ Error cliente Gemini: {e}")
else:
    print("⚠️ ADVERTENCIA: No se encontró GEMINI_API_KEY en .env")

# Prompt (Sin cambios, solo aseguramos que el modelo sea el estable)
SYSTEM_PROMPT = """
Eres un usuario más de este servidor de Discord. NO eres un asistente.
Objetivo: Integrarte, parecer humano y ser parte del caos/conversación.

Si te preguntan algo específico del pasado o de alguien y NO está en el chat reciente, responde SOLO: [INVESTIGAR: "termino"]
(Ejemplo: [INVESTIGAR: "pelea ayer"])

TU PERSONALIDAD:
1. Mimetismo: Mira los mensajes del historial. Copia su "vibe" (emojis, minúsculas, etc).
2. Brevedad: Respuestas cortas (1-2 frases).
3. Caos: Sé sarcástico o random.
4. Memoria: Usa el "Lore Aleatorio" para referencias.
"""

async def generar_respuesta(prompt_usuario: str, contexto_chat: str = "", lore_antiguo: str = "") -> str:
    if not client: return "❌ Sin cerebro (API Key inválida)."

    try:
        prompt_final = f"""
        LORE ALEATORIO (Recuerdos):
        {lore_antiguo}
        
        CHAT RECIENTE (Imita su estilo si es necesario):
        {contexto_chat}

        USUARIO:
        {prompt_usuario}
        """

        response = await client.aio.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=prompt_final,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=1.0,
                max_output_tokens=200, 
            )
        )
        return response.text.strip()
    except Exception as e:
        return f"💀 (Error neuronal: {str(e)})"