"""Download the full EMBER2024 dataset (train, test, challenge; all file types) from HuggingFace.

This is large (hundreds of GB once extracted). Edit DEST_DIR, then run:

    python custom/common/helper_scripts/download_all.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from thrember import download_dataset


def main() -> int:
    DEST_DIR = Path("../ember_data_full/")

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    abs_dest = DEST_DIR.resolve()
    before = {p.name for p in abs_dest.iterdir()}

    # download_dataset chdirs into the target; restore CWD on exit.
    cwd = os.getcwd()
    try:
        print(f"Downloading full dataset into {abs_dest} ...")
        download_dataset(str(abs_dest), split="all", file_type="all")
    finally:
        os.chdir(cwd)

    new_entries = sorted({p.name for p in abs_dest.iterdir()} - before)
    if new_entries:
        print("\nDownloaded:")
        for name in new_entries:
            print(f"  {name}")
    else:
        print("\nNo new files (already present).")

    print("\ndone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
