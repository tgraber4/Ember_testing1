"""
Count samples in each EMBER2024 .dat file in a folder, using file size only
(nothing is loaded into RAM).

X_*.dat : float32, shape (n, 2568)  -> n = bytes / (4 * 2568)
y_*.dat : int32/float32, shape (n,) -> n = bytes / 4   (use --y-classes for multi-label y)

Usage:
    python count_dat_samples.py <folder> [--dim 2568] [--y-classes 1]
"""
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--dim", type=int, default=2568, help="Feature dimension of X (EMBER2024 = 2568)")
    ap.add_argument("--y-classes", type=int, default=1, help="Columns in y (1 for binary labels)")
    args = ap.parse_args()

    files = sorted(args.folder.glob("*.dat"))
    if not files:
        raise SystemExit(f"No .dat files found in {args.folder}")

    print(f"{'file':<28}{'size (GB)':>12}{'samples':>16}")
    total_gb = 0.0
    for f in files:
        size = f.stat().st_size
        row_bytes = 4 * (args.dim if f.name.startswith("X_") else args.y_classes)
        n, rem = divmod(size, row_bytes)
        note = "" if rem == 0 else "  (WARNING: size not a multiple of row size - check --dim/--y-classes)"
        gb = size / 1024**3
        total_gb += gb
        print(f"{f.name:<28}{gb:>12.2f}{n:>16,}{note}")
    print(f"{'TOTAL':<28}{total_gb:>12.2f}")


if __name__ == "__main__":
    main()
