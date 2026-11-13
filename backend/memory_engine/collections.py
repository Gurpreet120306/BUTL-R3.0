from pymongo import ASCENDING, DESCENDING, TEXT


async def setup_indexes(db):
    observations = db.screen_observations
    await observations.create_index([("timestamp", DESCENDING)], name="observation_timestamp")
    await observations.create_index([
        ("application", TEXT), ("window_title", TEXT), ("extracted_text", TEXT),
        ("ai_summary", TEXT), ("important_findings", TEXT), ("detected_errors", TEXT),
    ], name="observation_text", default_language="english")
    for name in ("screen_observations", "assistant_conversations", "memory_summaries"):
        collection = db[name]
        await collection.create_index([("created_at", DESCENDING)])
        await collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, name="retention_ttl")
    await db.assistant_conversations.create_index([("question", TEXT), ("answer", TEXT)])
    await db.memory_summaries.create_index([("title", TEXT), ("summary", TEXT)])
