import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.core import db_service

async def main():
    await db_service.init_db()
    rows = await db_service.fetch_all("SELECT user_id, custom_prefix, birthday, coins FROM users")
    with open("scratch/db_output.txt", "w", encoding="utf-8") as f:
        f.write("=== USUARIOS EN LA BASE DE DATOS ===\n")
        for row in rows:
            f.write(f"ID: {row['user_id']} | Prefix: {row['custom_prefix']} | Bday: {row['birthday']} | Coins: {row['coins']}\n")
    await db_service.close_db()

if __name__ == "__main__":
    asyncio.run(main())
