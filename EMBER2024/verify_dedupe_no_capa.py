"""Verify the output of dedupe_remove_capa.py against the original folder.

Picks one random .jsonl file from each file type (Win32, Win64, Dot_Net, APK, ELF, PDF and the
challenge set) and compares the original with the output version of that file:
  - the output file exists
  - it has no caps/ttps/mbc fields
  - each hash appears exactly once
  - it has exactly the hashes of the original file (none lost, none added)
  - each record equals the original record once the Capa fields are removed

It also counts every sample in the output folder and compares the total with the documented
EMBER2024 size (3,238,315).

    python verify_dedupe_no_capa.py /path/to/ember_data_full
    python verify_dedupe_no_capa.py /path/to/ember_data_full --seed 1   # repeat the same selection
    python verify_dedupe_no_capa.py /path/to/ember_data_full --output /path/to/ember_data_full_no_capa
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HASH_KEYS = ("sha256", "sha1", "md5")
CAPA_FIELDS = ("caps", "ttps", "mbc")
FILE_TYPES = ("Win32", "Win64", "Dot_Net", "APK", "ELF", "PDF", "challenge")
EXPECTED_TOTAL = 2_626_000 + 606_000 + 6_315  # train + test + challenge (3,238,315)
CHUNK_SIZE = 16 * 1024 * 1024


def group_by_type(files: list[Path]) -> dict[str, list[Path]]:
    """Group files by file type taken from the name, e.g. 2023-09-24_2023-09-30_Win32_train.jsonl."""
    groups: dict[str, list[Path]] = {}
    for path in files:
        for file_type in FILE_TYPES:
            if f"_{file_type}_" in path.name:
                groups.setdefault(file_type, []).append(path)
                break
    return groups


def digest(obj: dict) -> bytes:
    return hashlib.blake2b(json.dumps(obj, sort_keys=True).encode(), digest_size=16).digest()


def read_records(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def count_lines(path: Path) -> int:
    """Count lines by counting newlines in binary chunks (fast, low memory)."""
    count = 0
    last_byte = b"\n"
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            count += chunk.count(b"\n")
            last_byte = chunk[-1:]
    if last_byte != b"\n":
        count += 1
    return count


def verify_file(src: Path, dst: Path) -> tuple[list[str], int]:
    """Return (problems, unique records in the output file). No problems means the file is correct."""
    if not dst.exists():
        return ["output file is missing"], 0

    expected: dict[str, bytes] = {}  # hash -> digest of original record without Capa fields
    hash_key = None
    for obj in read_records(src):
        if hash_key is None:
            hash_key = next((k for k in HASH_KEYS if k in obj), None)
            if hash_key is None:
                return [f"no hash field among {HASH_KEYS} in original"], 0
        for field in CAPA_FIELDS:
            obj.pop(field, None)
        expected.setdefault(obj[hash_key], digest(obj))

    seen = set()
    capa_records = duplicate_hashes = changed = unexpected = 0
    for obj in read_records(dst):
        if any(field in obj for field in CAPA_FIELDS):
            capa_records += 1
        h = obj.get(hash_key)
        if h in seen:
            duplicate_hashes += 1
        seen.add(h)
        if h not in expected:
            unexpected += 1
        elif expected[h] != digest(obj):
            changed += 1

    problems = []
    missing = len(expected.keys() - seen)
    if capa_records:
        problems.append(f"{capa_records:,} records still have Capa fields")
    if duplicate_hashes:
        problems.append(f"{duplicate_hashes:,} duplicated hashes")
    if missing:
        problems.append(f"{missing:,} hashes from the original are missing")
    if unexpected:
        problems.append(f"{unexpected:,} hashes that are not in the original")
    if changed:
        problems.append(f"{changed:,} records differ from the original beyond the Capa fields")
    return problems, len(seen)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify deduplicated, Capa-free EMBER2024 shards.")
    parser.add_argument("input", type=Path, help="original folder (e.g. ember_data_full)")
    parser.add_argument("--output", type=Path, help='output folder (default: sibling "<input>_no_capa")')
    parser.add_argument("--seed", type=int, help="random seed, to repeat the same file selection")
    args = parser.parse_args()

    src_root = args.input.resolve()
    dst_root = (args.output or src_root.with_name(src_root.name + "_no_capa")).resolve()
    if not src_root.is_dir():
        print(f"Not a directory: {src_root}", file=sys.stderr)
        return 1
    if not dst_root.is_dir():
        print(f"Not a directory: {dst_root}", file=sys.stderr)
        return 1

    files = sorted(src_root.rglob("*.jsonl"))
    if not files:
        print(f"No .jsonl files found in {src_root}")
        return 1
    print(f"Original: {src_root}\nOutput:   {dst_root}")

    rng = random.Random(args.seed)
    chosen = [rng.choice(group) for group in group_by_type(files).values()]
    print(f"\nChecking one random file per type ({len(chosen)} files):")

    failed = 0
    for i, src in enumerate(chosen, 1):
        rel = src.relative_to(src_root)
        problems, count = verify_file(src, dst_root / rel)
        if problems:
            failed += 1
            print(f"[{i}/{len(chosen)}] FAIL {rel}")
            for p in problems:
                print(f"    - {p}")
        else:
            print(f"[{i}/{len(chosen)}] ok   {rel}: {count:,} unique records")

    print("\nCounting all samples in the output folder ...")
    out_files = sorted(dst_root.rglob("*.jsonl"))
    total = sum(count_lines(p) for p in out_files)
    total_ok = total == EXPECTED_TOTAL
    print(f"Output files: {len(out_files)} (original has {len(files)})")
    print(f"Total samples in output: {total:,}  (documented: {EXPECTED_TOTAL:,})  "
          f"{'matches' if total_ok else 'DOES NOT MATCH'}")

    passed = failed == 0 and total_ok and len(out_files) == len(files)
    print(f"\nSampled files failed: {failed}")
    print("RESULT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
