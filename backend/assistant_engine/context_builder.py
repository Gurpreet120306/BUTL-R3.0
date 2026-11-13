import json


def build_context(memories, budget: int = 18000) -> tuple[str, list[str]]:
    records, ids, used = [], [], 0
    for memory in memories[:6]:
        record = {"memory_id": memory.observation_id, "timestamp": memory.timestamp.isoformat(),
                  "application": memory.application, "window_title": memory.window_title,
                  "extracted_text": memory.extracted_text[:4500], "summary": memory.ai_summary[:2000],
                  "detected_errors": memory.detected_errors[:10]}
        serialized = json.dumps(record, ensure_ascii=False)
        if used + len(serialized) > budget:
            break
        records.append(record)
        ids.append(memory.observation_id)
        used += len(serialized)
    return json.dumps({"untrusted_memory_records": records}, ensure_ascii=False), ids
