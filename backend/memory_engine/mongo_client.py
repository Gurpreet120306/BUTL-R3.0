from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from backend.shared.contracts import ServiceStatus


class MemoryUnavailable(RuntimeError):
    pass


class MongoConnection:
    def __init__(self, uri: str, database: str):
        self.client = AsyncMongoClient(uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000,
                                       socketTimeoutMS=5000, tz_aware=True)
        self.db = self.client[database]

    async def health(self) -> ServiceStatus:
        try:
            await self.client.admin.command("ping")
            return ServiceStatus(available=True, message="Local MongoDB is connected")
        except PyMongoError:
            return ServiceStatus(available=False, message="MongoDB unavailable. Start the local MongoDB service")

    async def close(self):
        await self.client.close()
