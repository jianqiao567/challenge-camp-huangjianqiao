#!/usr/bin/env python3
"""clean_basic.py

Basic cleaning for raw/d3/chat_sessions_dirty.csv

Usage:
    python clean_basic.py --input raw/d3/chat_sessions_dirty.csv --output raw/d3/chat_sessions_clean.csv
"""
import argparse
import os
import sys
from typing import Optional

import pandas as pd
print("Hello World")

def strip_object_columns(df: pd.DataFrame) -> pd.DataFrame:
    obj_cols = df.select_dtypes(include=[object, "string"]).columns
    for c in obj_cols:
        df[c] = df[c].where(df[c].notna(), None)
        df[c] = df[c].astype(object).map(lambda v: v.strip() if isinstance(v, str) else v)
    return df


def find_column(df: pd.DataFrame, candidates):
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in cols:
            return cols[cand]
    return None


def parse_timestamp_column(df: pd.DataFrame) -> Optional[str]:
    ts_cands = ["timestamp", "time", "created_at", "created", "ts", "date"]
    col = find_column(df, ts_cands)
    if col is None:
        return None
    try:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True, infer_datetime_format=True)
        # normalize to ISO string (UTC)
        df[col] = df[col].dt.tz_convert("UTC")
    except Exception:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df.rename(columns={col: "timestamp"}, inplace=True)
    return "timestamp"


def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    # drop rows that are completely empty
    df = df.dropna(how="all")

    # trim whitespace
    df = strip_object_columns(df)

    # drop exact duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)

    # parse timestamp if present
    ts_col = parse_timestamp_column(df)

    # drop rows missing essential fields if present
    msg_col = find_column(df, ["message", "text", "content"])
    usr_col = find_column(df, ["user_id", "user", "sender", "actor"])
    required = []
    if msg_col:
        required.append(msg_col)
    if usr_col:
        required.append(usr_col)
    if required:
        df = df.dropna(subset=required)

    # deduplicate by session and timestamp if possible
    sess_col = find_column(df, ["session_id", "session", "conversation_id"])
    if sess_col and ts_col:
        df = df.sort_values("timestamp").drop_duplicates(subset=[sess_col, "timestamp"], keep="first")

    return df


def main(argv=None):
    parser = argparse.ArgumentParser(description="Basic cleaner for chat_sessions_dirty.csv")
    parser.add_argument("--input", "-i", default=os.path.join("raw", "d3", "chat_sessions_dirty.csv"))
    parser.add_argument("--output", "-o", default=os.path.join("raw", "d3", "chat_sessions_clean.csv"))
    args = parser.parse_args(argv)

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        sys.exit(2)

    df = pd.read_csv(args.input, dtype=str, keep_default_na=True, na_values=["", "NA", "None"]) 

    cleaned = basic_clean(df)

    cleaned.to_csv(args.output, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Cleaned rows: {len(cleaned)}")
    print(f"Wrote cleaned CSV to: {args.output}")


if __name__ == "__main__":
    main()
