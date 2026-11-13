"""Run from project root: python -m scripts.setup_indexes."""
import asyncio

from backend.memory_engine import MemoryManager, MongoConnection
from backend.shared.config import Config


async def main():
    config = Config()
    connection = MongoConnection(config.mongodb_uri, config.mongodb_db)
    try:
        await MemoryManager(connection.db).ensure_indexes()
        print(f"BUTL-R indexes ready in {config.mongodb_db}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
