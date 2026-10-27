"""Check whether samples are duplicated inside EMBER2024 .jsonl shards.

For each file: groups records by hash, counts how many hashes appear more than once,
and reports which top-level fields differ between the copies (e.g. caps).

    python check_duplicates.py shard1.jsonl [shard2.jsonl ...]
    python check_duplicates.py /path/to/ember_data_full --per-type 1
    python check_duplicates.py /path/to/ember_data_full --output duplicate_check.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HASH_KEYS = ("sha256", "sha1", "md5")
FILE_TYPES = ("Win32", "Win64", "Dot_Net", "APK", "ELF", "PDF")


class Tee:
    """Write to several streams at once (terminal and output file)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)

    def flush(self):
        for s in self.streams:
            s.flush()


def pick_files(folder: Path, per_type: int) -> list[Path]:
    """First `per_type` train shards of each file type, plus nothing from challenge."""
    files = []
    for file_type in FILE_TYPES:
        matches = sorted(folder.rglob(f"*_{file_type}_train.jsonl"))
        files.extend(matches[:per_type])
    return files


def is_empty(value) -> bool:
    return value in (None, "", [], {})


def check_file(path: Path) -> None:
    records = defaultdict(list)
    hash_key = None
    keys_seen = None
    total = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            total += 1
            if hash_key is None:
                keys_seen = list(obj.keys())
                hash_key = next((k for k in HASH_KEYS if k in obj), None)
                if hash_key is None:
                    print(f"{path.name}: no hash field among {HASH_KEYS}; keys: {keys_seen}")
                    return
            records[obj[hash_key]].append(obj)

    counts = Counter(len(v) for v in records.values())
    print(f"\n=== {path.name} ===")
    print(f"records: {total:,}  unique {hash_key}: {len(records):,}")
    print(f"copies per hash: {dict(sorted(counts.items()))}")

    dupes = [v for v in records.values() if len(v) > 1]
    if not dupes:
        print("no duplicated hashes")
        return

    identical = 0
    differing_fields = Counter()
    caps_patterns = Counter()
    for group in dupes:
        if all(g == group[0] for g in group[1:]):
            identical += 1
            continue
        all_keys = set().union(*(g.keys() for g in group))
        for key in all_keys:
            if len({json.dumps(g.get(key), sort_keys=True) for g in group}) > 1:
                differing_fields[key] += 1
        if "caps" in all_keys:
            caps_patterns[tuple(sorted("empty" if is_empty(g.get("caps")) else "filled" for g in group))] += 1

    print(f"duplicated hashes: {len(dupes):,}  (fully identical copies: {identical:,})")
    print("fields that differ between copies (number of hashes affected):")
    for key, n in differing_fields.most_common():
        print(f"  {key}: {n:,}")
    if "caps" in (keys_seen or []):
        print(f"caps per copy-set (empty vs filled): {dict(caps_patterns)}")
    else:
        print(f"no top-level 'caps' field in this file type; keys: {keys_seen}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for duplicated samples in EMBER2024 shards.")
    parser.add_argument("paths", nargs="+", type=Path, help=".jsonl files, or a data folder")
    parser.add_argument("--per-type", type=int, default=1, help="shards per file type when given a folder")
    parser.add_argument("--output", type=Path, help="also write the results to this text file")
    args = parser.parse_args()

    files: list[Path] = []
    for p in args.paths:
        if p.is_dir():
            files.extend(pick_files(p, args.per_type))
        elif p.is_file():
            files.append(p)
        else:
            print(f"Not found: {p}", file=sys.stderr)
            return 1

    if not files:
        print("No .jsonl files found")
        return 1
    if args.output is None:
        for path in files:
            check_file(path)
        return 0

    with open(args.output, "w", encoding="utf-8") as out:
        stdout = sys.stdout
        sys.stdout = Tee(stdout, out)
        try:
            for path in files:
                check_file(path)
        finally:
            sys.stdout = stdout
    print(f"\nResults written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
