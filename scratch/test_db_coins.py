import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.core import db_service

async def main():
    await db_service.init_db()
    user_id = 716845090500247613
    
    # Obtener monedas actuales
    coins_before = await db_service.get_user_coins(user_id)
    print(f"Monedas antes: {coins_before}")
    
    # Intentar añadir
    print("Añadiendo 12 monedas...")
    await db_service.add_user_coins(user_id, 12)
    
    # Obtener monedas después
    coins_after = await db_service.get_user_coins(user_id)
    print(f"Monedas después: {coins_after}")
    
    await db_service.close_db()

if __name__ == "__main__":
    asyncio.run(main())
