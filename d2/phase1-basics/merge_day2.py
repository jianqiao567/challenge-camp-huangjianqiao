#!/usr/bin/env python3
"""Merge raw/d2 source files into raw/d2/merged.jsonl."""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, List


def load_json_records(path: Path) -> List[Any]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    payload = json.loads(text)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "results" in payload and isinstance(payload["results"], list):
            return payload["results"]
        if "items" in payload and isinstance(payload["items"], list):
            return payload["items"]
        if len(payload) == 1:
            first_value = next(iter(payload.values()))
            if isinstance(first_value, list):
                return first_value
        return [payload]

    raise ValueError(f"Unsupported JSON payload in {path}")


def collect_source_files(input_dir: Path, output_file: Path) -> List[Path]:
    files = []
    for path in sorted(input_dir.iterdir()):
        if path == output_file:
            continue
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".ndjson"}:
            files.append(path)
    return files


def normalize_record(record: Any) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True)


def dedupe_records(records: Iterable[Any]) -> List[Any]:
    seen = set()
    unique: List[Any] = []
    for record in records:
        key = normalize_record(record)
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique


def write_jsonl(records: Iterable[Any], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")


def validate_record_for_file(record: Any, path: Path):
    """Return (is_valid: bool, reason: str)."""
    name = path.stem.lower()
    # user behavior expected fields
    if "user_behavior" in name or "behavior" in name:
        required = ["uid", "time", "action", "content"]
    elif "tool_result" in name or "tool" in name:
        required = ["trace_id", "tool", "status", "output"]
    else:
        # unknown source: accept but no strict validation
        return True, "no-validation"

    missing = []
    for k in required:
        if k not in record or record[k] is None:
            missing.append(k)
        else:
            # treat blank strings as missing
            v = record[k]
            if isinstance(v, str) and not v.strip():
                missing.append(k)

    if missing:
        return False, f"missing:{','.join(missing)}"
    return True, "ok"


def main(argv=None) -> int:
    default_input_dir = Path(__file__).resolve().parent.parent
    default_output = default_input_dir / "merged.jsonl"

    parser = argparse.ArgumentParser(description="Merge D2 source files into merged.jsonl")
    parser.add_argument("--input", "-i", type=Path, default=default_input_dir,
                        help="Input directory containing D2 source files")
    parser.add_argument("--output", "-o", type=Path, default=default_output,
                        help="Output merged JSONL file")
    parser.add_argument("--min-rows", type=int, default=8,
                        help="Minimum number of deduplicated output rows")
    args = parser.parse_args(argv)

    input_dir = args.input
    output_file = args.output

    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")

    source_files = collect_source_files(input_dir, output_file)
    if not source_files:
        raise SystemExit(f"No JSON or JSONL source files found in {input_dir}")

    total_read = 0
    kept_records: List[Any] = []
    log_lines: List[str] = []

    for path in source_files:
        recs = load_json_records(path)
        total_read += len(recs)
        kept = []
        dropped = []
        for r in recs:
            valid, reason = validate_record_for_file(r, path)
            if not valid:
                dropped.append((r, reason))
            else:
                kept.append(r)

        log_lines.append(f"File {path.name}: read={len(recs)} kept={len(kept)} dropped={len(dropped)}")
        if dropped:
            # include up to first 3 dropped examples
            for ex, reason in dropped[:3]:
                log_lines.append(f"  dropped example reason={reason}: {json.dumps(ex, ensure_ascii=False)[:400]}")

        kept_records.extend(kept)

    unique_records = dedupe_records(kept_records)

    # write clean.log
    log_path = input_dir / "clean.log"
    with log_path.open("w", encoding="utf-8") as lf:
        lf.write(f"total_read={total_read}\n")
        lf.write("\n".join(log_lines))
        lf.write("\n")

    if len(unique_records) < args.min_rows:
        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(f"ERROR: deduplicated count {len(unique_records)} < min_rows {args.min_rows}\n")
        raise SystemExit(
            f"Deduplicated record count {len(unique_records)} is less than required minimum {args.min_rows}. See {log_path}"
        )

    write_jsonl(unique_records, output_file)

    print(f"Read {total_read} records from {len(source_files)} source files")
    print(f"Wrote {len(unique_records)} deduplicated records to {output_file}")
    print(f"Wrote validation log to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
