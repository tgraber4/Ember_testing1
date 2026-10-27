"""Count samples (lines) in every .jsonl file under a folder.

    python count_samples.py /path/to/ember_data_full
    python count_samples.py /path/to/ember_data_full --no-recursive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

CHUNK_SIZE = 16 * 1024 * 1024


def count_lines(path: Path) -> int:
    """Count lines by counting newlines in binary chunks (fast, low memory)."""
    count = 0
    last_byte = b"\n"
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            count += chunk.count(b"\n")
            last_byte = chunk[-1:]
    if last_byte != b"\n":
        count += 1  # final line without a trailing newline
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Count samples in each .jsonl file in a folder.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--no-recursive", action="store_true", help="only look at files directly in the folder")
    args = parser.parse_args()

    if not args.folder.is_dir():
        print(f"Not a directory: {args.folder}", file=sys.stderr)
        return 1

    pattern = "*.jsonl"
    files = sorted(args.folder.glob(pattern) if args.no_recursive else args.folder.rglob(pattern))
    if not files:
        print(f"No .jsonl files found in {args.folder}")
        return 1

    total = 0
    for path in files:
        n = count_lines(path)
        total += n
        print(f"{n:>12,}  {path.relative_to(args.folder)}")

    print(f"{total:>12,}  TOTAL ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
