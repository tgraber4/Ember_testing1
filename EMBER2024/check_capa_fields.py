"""Check how the Capa fields (caps, ttps, mbc) look in EMBER2024 .jsonl shards.

For every record each field is classified as missing (key absent), empty, or filled.
Then records are paired by hash and the states of the two copies are reported in file
order, separately for identical and non-identical pairs.

    python check_capa_fields.py shard1.jsonl [shard2.jsonl ...]
    python check_capa_fields.py /path/to/ember_data_full --per-type 1 --output capa_fields.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HASH_KEYS = ("sha256", "sha1", "md5")
CAPA_FIELDS = ("caps", "ttps", "mbc")
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
    files = []
    for file_type in FILE_TYPES:
        files.extend(sorted(folder.rglob(f"*_{file_type}_train.jsonl"))[:per_type])
    return files


def state(obj: dict, key: str) -> str:
    if key not in obj:
        return "missing"
    return "empty" if obj[key] in (None, "", [], {}) else "filled"


def fmt(counter: Counter) -> str:
    if not counter:
        return "  (none)"
    return "\n".join(f"  {k}: {n:,}" for k, n in counter.most_common())


def check_file(path: Path) -> None:
    groups = defaultdict(list)
    hash_key = None
    total = 0
    record_states = {field: Counter() for field in CAPA_FIELDS}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            total += 1
            if hash_key is None:
                hash_key = next((k for k in HASH_KEYS if k in obj), None)
                if hash_key is None:
                    print(f"{path.name}: no hash field among {HASH_KEYS}; keys: {list(obj.keys())}")
                    return
            states = tuple(state(obj, field) for field in CAPA_FIELDS)
            for field, s in zip(CAPA_FIELDS, states):
                record_states[field][s] += 1
            # keep only the states and a digest of the record, not the record itself
            digest = hashlib.blake2b(json.dumps(obj, sort_keys=True).encode(), digest_size=16).digest()
            groups[obj[hash_key]].append((states, digest))

    print(f"\n=== {path.name} ===")
    print(f"records: {total:,}  unique {hash_key}: {len(groups):,}")
    for field in CAPA_FIELDS:
        print(f"all records, {field}: {dict(record_states[field])}")

    pairs = [g for g in groups.values() if len(g) == 2]
    print(f"pairs: {len(pairs):,}  (hashes with other copy counts: {len(groups) - len(pairs):,})")

    identical = Counter()
    different = Counter()
    for (first_states, first_digest), (second_states, second_digest) in pairs:
        # state of (first copy in file, second copy in file) for each capa field
        combo = " ".join(
            f"{field}={a}/{b}" for field, a, b in zip(CAPA_FIELDS, first_states, second_states)
        )
        (identical if first_digest == second_digest else different)[combo] += 1

    print("identical pairs, by (first/second) state:")
    print(fmt(identical))
    print("non-identical pairs, by (first/second) state:")
    print(fmt(different))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Capa field states in EMBER2024 shards.")
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
