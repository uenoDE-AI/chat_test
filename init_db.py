# init_db.py
import aiosqlite, asyncio, pathlib

DB_PATH = "chat.db"

async def init():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            ts TEXT,
            metadata TEXT
        )
        """)
        await db.commit()
    print(f"✅ {pathlib.Path(DB_PATH).resolve()} にテーブルを作成しました")

asyncio.run(init())
