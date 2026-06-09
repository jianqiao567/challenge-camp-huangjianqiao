import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_D5 = ROOT / "raw" / "d5"
OUTPUT_DIR = ROOT / "generated" / "d5"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IGNORE_EVENT_TYPES = {"temporary_instruction"}
FORGET_EVENT_TYPES = {"forget"}
KNOWN_PREFERENCE_KEYWORDS = ["emoji", "输出", "会议纪要", "回答", "风格", "样式"]


def normalize_text(text):
    if text is None:
        return ""
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    text = text.lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    return text.strip()


def parse_time(text):
    if not text:
        return None
    text = str(text).strip()
    text = text.replace("T", " ").replace("Z", "+0000")
    text = re.sub(r"年|月", "-", text)
    text = re.sub(r"日", "", text)
    text = re.sub(r"(\+\d{2}):?(\d{2})$", r"+\1\2", text)
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M%z",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    digits = re.findall(r"\d+", text)
    if len(digits) >= 3:
        try:
            year, month, day = map(int, digits[:3])
            hour = int(digits[3]) if len(digits) > 3 else 0
            minute = int(digits[4]) if len(digits) > 4 else 0
            second = int(digits[5]) if len(digits) > 5 else 0
            return datetime(year, month, day, hour, minute, second)
        except ValueError:
            return None
    return None


def normalize_key(event_type, content):
    raw = normalize_text(content)
    for keyword in KNOWN_PREFERENCE_KEYWORDS:
        if keyword in raw:
            return keyword
    if event_type.startswith("knowledge"):
        return "knowledge:" + raw[:40]
    if event_type.startswith("tool"):
        return "tool:" + raw[:40]
    if event_type == "preference":
        return raw[:40] or "preference"
    return raw[:40] or event_type


def load_jsonl(path):
    events = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                record["source_file"] = path.name
                events.append(record)
            except json.JSONDecodeError:
                continue
    return events


def load_snapshots(path):
    snapshots = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            event = {
                "event_id": f"snapshot-{index}",
                "uid": row.get("uid", ""),
                "source": "snapshot",
                "event_type": row.get("scope", "preference") if row.get("scope") else "preference",
                "content": row.get("memory_value", ""),
                "time": row.get("last_seen", ""),
                "ttl": row.get("version", ""),
                "confidence": "snapshot",
                "memory_key": row.get("memory_key", ""),
                "note": row.get("note", ""),
                "source_file": path.name,
            }
            snapshots.append(event)
    return snapshots


def build_timeline(events):
    records = []
    for event in events:
        parsed_time = parse_time(event.get("time") or "")
        records.append((parsed_time or datetime.min, event))
    records.sort(key=lambda item: (item[0], item[1].get("event_id", "")))
    return [item[1] for item in records]


def is_temporary(event):
    return event.get("event_type", "").lower() in IGNORE_EVENT_TYPES


def is_forget(event):
    return event.get("event_type", "").lower() in FORGET_EVENT_TYPES


def extract_reason(evidence_records):
    return [
        {
            "event_id": record.get("event_id"),
            "time": record.get("time"),
            "source": record.get("source"),
            "content": record.get("content"),
            "ttl": record.get("ttl"),
        }
        for record in evidence_records
    ]


def merge_user_events(user_events):
    memory = {}
    history = defaultdict(list)
    conflicts = []
    reversed_events = list(reversed(user_events))
    for event in reversed_events:
        if is_temporary(event):
            continue
        if is_forget(event):
            target = normalize_text(event.get("content", ""))
            removed_keys = []
            for key, item in list(memory.items()):
                if target and target in item["normalized_content"]:
                    removed_keys.append(key)
                    del memory[key]
            conflicts.append(
                {
                    "uid": event.get("uid"),
                    "type": "forget_action",
                    "reason": f"用户要求遗忘: {event.get('content')}",
                    "evidence": extract_reason([event]),
                    "removed_keys": removed_keys,
                }
            )
            continue
        event_type = event.get("event_type", "").lower()
        content = event.get("content", "")
        normalized_content = normalize_text(content)
        key = event.get("memory_key") or normalize_key(event_type, content)
        chosen_key = normalize_text(key)[:60] or event_type
        item = {
            "event_id": event.get("event_id"),
            "uid": event.get("uid"),
            "source": event.get("source"),
            "event_type": event_type,
            "content": content,
            "normalized_content": normalized_content,
            "memory_key": chosen_key,
            "time": event.get("time"),
            "parsed_time": parse_time(event.get("time") or ""),
            "ttl": event.get("ttl"),
            "confidence": event.get("confidence"),
            "source_file": event.get("source_file"),
        }
        if chosen_key in memory:
            existing = memory[chosen_key]
            if existing["normalized_content"] != normalized_content:
                conflicts.append(
                    {
                        "uid": event.get("uid"),
                        "type": "conflict",
                        "memory_key": chosen_key,
                        "reason": "覆盖旧条目",
                        "evidence": extract_reason([existing, item]),
                    }
                )
        memory[chosen_key] = item
        history[chosen_key].append(item)
    return memory, history, conflicts


def deduplicate_memory(memory_by_key):
    deduped = {}
    seen = {}
    for key, item in memory_by_key.items():
        duplicate_key = (item["event_type"], item["normalized_content"])
        if duplicate_key in seen:
            existing = seen[duplicate_key]
            existing_time = existing.get("parsed_time") or datetime.min
            current_time = item.get("parsed_time") or datetime.min
            if current_time > existing_time:
                deduped[key] = item
                seen[duplicate_key] = item
            continue
        deduped[key] = item
        seen[duplicate_key] = item
    return deduped


def save_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def summarize(active_records, conflict_records):
    summary = {
        "users": len(active_records),
        "total_active_records": len(active_records),
        "total_conflicts": len(conflict_records),
    }
    return summary


def main():
    events = load_jsonl(RAW_D5 / "memory_events_raw.jsonl")
    events.extend(load_snapshots(RAW_D5 / "user_memory_snapshots_raw.csv"))
    users = defaultdict(list)
    for event in build_timeline(events):
        uid = str(event.get("uid", "unknown")).strip().lower()
        users[uid].append(event)
    output_records = []
    output_history = []
    output_conflicts = []
    for uid, event_list in users.items():
        memory, history, conflicts = merge_user_events(event_list)
        memory = deduplicate_memory(memory)
        for item in memory.values():
            output_records.append(item)
        for key, entries in history.items():
            for entry in entries:
                output_history.append({**entry, "memory_key": key})
        for conflict in conflicts:
            output_conflicts.append(conflict)
    save_jsonl(OUTPUT_DIR / "cleaned_memory.jsonl", output_records)
    save_jsonl(OUTPUT_DIR / "memory_history.jsonl", output_history)
    save_jsonl(OUTPUT_DIR / "conflicts.jsonl", output_conflicts)
    summary = summarize(output_records, output_conflicts)
    print("清洗完成，输出路径:")
    print(f"- {OUTPUT_DIR / 'cleaned_memory.jsonl'}")
    print(f"- {OUTPUT_DIR / 'memory_history.jsonl'}")
    print(f"- {OUTPUT_DIR / 'conflicts.jsonl'}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
