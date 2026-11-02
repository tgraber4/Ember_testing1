"""Deduplicate EMBER2024 .jsonl shards and remove the Capa fields from every sample.

Reads every .jsonl file under the input folder and writes a cleaned copy to a sibling
folder named "<input>_no_capa", keeping the same sub-folder layout. The input files are
never modified.

For each file, records are deduplicated by hash (the first occurrence is kept) after the
Capa fields (caps, ttps, mbc) are removed. A dropped record should be identical to the kept
one once those fields are gone; any that are not are counted as mismatches.

    python dedupe_remove_capa.py /path/to/ember_data_full
    python dedupe_remove_capa.py /path/to/ember_data_full --output /path/to/out --overwrite
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HASH_KEYS = ("sha256", "sha1", "md5")
CAPA_FIELDS = ("caps", "ttps", "mbc")


def digest(obj: dict) -> bytes:
    return hashlib.blake2b(json.dumps(obj, sort_keys=True).encode(), digest_size=16).digest()


def process_file(src: Path, dst: Path) -> tuple[int, int, int]:
    """Write the cleaned copy of src to dst. Returns (records read, written, mismatches)."""
    seen: dict[str, bytes] = {}
    read = written = mismatches = 0
    hash_key = None

    tmp = dst.with_name(dst.name + ".tmp")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "r", encoding="utf-8") as fin, open(tmp, "w", encoding="utf-8", newline="\n") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            read += 1
            if hash_key is None:
                hash_key = next((k for k in HASH_KEYS if k in obj), None)
                if hash_key is None:
                    raise ValueError(f"{src}: no hash field among {HASH_KEYS}")
            for field in CAPA_FIELDS:
                obj.pop(field, None)

            sample_hash = obj[hash_key]
            d = digest(obj)
            if sample_hash in seen:
                if seen[sample_hash] != d:
                    mismatches += 1
                continue
            seen[sample_hash] = d
            fout.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
            written += 1

    os.replace(tmp, dst)  # only a complete file ever has the final name
    return read, written, mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description="Deduplicate EMBER2024 shards and remove Capa fields.")
    parser.add_argument("input", type=Path, help="folder containing the .jsonl files (e.g. ember_data_full)")
    parser.add_argument("--output", type=Path, help='output folder (default: sibling "<input>_no_capa")')
    parser.add_argument("--overwrite", action="store_true", help="redo files that already exist in the output")
    args = parser.parse_args()

    src_root = args.input.resolve()
    if not src_root.is_dir():
        print(f"Not a directory: {src_root}", file=sys.stderr)
        return 1
    dst_root = (args.output or src_root.with_name(src_root.name + "_no_capa")).resolve()
    if dst_root == src_root or src_root in dst_root.parents or dst_root in src_root.parents:
        print("Output folder must be separate from the input folder", file=sys.stderr)
        return 1

    files = sorted(src_root.rglob("*.jsonl"))
    if not files:
        print(f"No .jsonl files found in {src_root}")
        return 1
    print(f"Input:  {src_root}\nOutput: {dst_root}\nFiles:  {len(files)}")

    total_read = total_written = total_mismatches = skipped = 0
    for i, src in enumerate(files, 1):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        if dst.exists() and not args.overwrite:
            skipped += 1
            print(f"[{i}/{len(files)}] skip (exists) {rel}")
            continue
        read, written, mismatches = process_file(src, dst)
        total_read += read
        total_written += written
        total_mismatches += mismatches
        print(f"[{i}/{len(files)}] {rel}: read {read:,}, wrote {written:,}, mismatched duplicates {mismatches:,}")

    print(f"\nProcessed {len(files) - skipped} files ({skipped} skipped)")
    print(f"Records read:    {total_read:,}")
    print(f"Records written: {total_written:,}")
    print(f"Duplicates whose other copy differed beyond the Capa fields: {total_mismatches:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
