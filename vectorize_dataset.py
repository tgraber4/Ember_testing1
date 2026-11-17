"""
Vectorize the EMBER2024 dataset and write the .dat files to a chosen output directory.

thrember.create_vectorized_features() writes the .dat files into the same folder as the
.jsonl files. This script reuses thrember's own helpers but takes a separate output folder.

Outputs (in --output-dir):
    X_train.dat, y_train.dat, X_test.dat, y_test.dat, X_challenge.dat, y_challenge.dat
    label_map.json   (string label -> column index; empty for --label-type label)

Example (inside the container):
    apptainer exec --bind /cluster/pixstor/euh46-lab \
        --env PYTHONPATH=/cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/EMBER2024/src \
        ember.sif python vectorize_dataset.py \
            --data-dir /cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/ember_data_full \
            --output-dir /cluster/pixstor/euh46-lab/EmberEnsemble/Tyler/vectorized \
            --workers 16
"""
import argparse
import functools
import json
import multiprocessing
from pathlib import Path


def count_rows(paths):
    return sum(1 for p in paths for _ in p.open())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", required=True, type=Path,
                    help="Folder containing the extracted .jsonl files")
    ap.add_argument("--output-dir", required=True, type=Path,
                    help="Folder where the .dat files will be written (created if missing)")
    ap.add_argument("--label-type", default="label",
                    help="label, family, behavior, file_property, packer, exploit, group (default: label)")
    ap.add_argument("--class-min", type=int, default=10,
                    help="Minimum instances of a class to keep it (non-binary label types)")
    ap.add_argument("--workers", type=int, default=None,
                    help="Worker processes (default: all CPUs the machine reports; set this to your "
                         "allocated core count on a cluster)")
    args = ap.parse_args()

    if not args.data_dir.is_dir():
        ap.error(f"--data-dir does not exist: {args.data_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # thrember calls multiprocessing.Pool() with no arguments; cap the worker count here.
    if args.workers:
        multiprocessing.Pool = functools.partial(multiprocessing.Pool, args.workers)

    from thrember import features, model

    extractor = features.PEFeatureExtractor()
    ignore_tags = {"", "win32", "win64", "elf", "linux", "pdf", "apk", "android"}
    label_type = args.label_type

    train_paths = model.gather_feature_paths(args.data_dir, "train")
    test_paths = model.gather_feature_paths(args.data_dir, "test")
    challenge_paths = model.gather_feature_paths(args.data_dir, "challenge")
    print("Counting rows")
    train_n, test_n, challenge_n = (count_rows(p) for p in (train_paths, test_paths, challenge_paths))
    print(f"train={train_n} test={test_n} challenge={challenge_n}")

    label_map = {}
    if label_type != "label":
        for paths, n in ((train_paths, train_n), (test_paths, test_n)):
            counts = model.read_label_subset(paths, n, label_type)
            for lab, count in counts.items():
                if lab in ignore_tags or lab in label_map:
                    continue
                if count >= args.class_min:
                    label_map[lab] = len(label_map)
            if paths is train_paths:
                # Match thrember: the train set is vectorized before test labels are added
                print("Vectorizing training set")
                model.vectorize_subset(args.output_dir / "X_train.dat", args.output_dir / "y_train.dat",
                                       train_paths, extractor, train_n, label_type, label_map)
        # Test labels may have added classes, so the train y file must have the final width
        # only if new labels appeared; thrember has the same behavior, so we keep it.
    else:
        print("Vectorizing training set")
        model.vectorize_subset(args.output_dir / "X_train.dat", args.output_dir / "y_train.dat",
                               train_paths, extractor, train_n, label_type, label_map)

    print("Vectorizing test set")
    model.vectorize_subset(args.output_dir / "X_test.dat", args.output_dir / "y_test.dat",
                           test_paths, extractor, test_n, label_type, label_map)

    print("Vectorizing challenge set")
    model.vectorize_subset(args.output_dir / "X_challenge.dat", args.output_dir / "y_challenge.dat",
                           challenge_paths, extractor, challenge_n)

    with open(args.output_dir / "label_map.json", "w") as f:
        json.dump(label_map, f, indent=2)
    print(f"Done. Files written to {args.output_dir}")


if __name__ == "__main__":
    main()
