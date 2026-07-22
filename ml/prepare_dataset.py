"""Create the normalized 12-feature dataset used by the ML pipeline."""

import argparse
import csv
from pathlib import Path

from features.feature_extractor import FEATURE_NAMES
from scripts.train_phishing_model import load_dataset


ROOT = Path(__file__).resolve().parents[1]


def prepare(input_path: Path, output_path: Path) -> int:
    features, labels, _ = load_dataset(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow([*FEATURE_NAMES, "label"])
        for values, label in zip(features, labels):
            writer.writerow([*map(int, values), int(label)])
    return len(labels)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data" / "raw" / "phishing_websites.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "processed" / "feature_dataset.csv",
    )
    args = parser.parse_args()
    rows = prepare(args.input, args.output)
    print(f"Wrote {rows:,} rows to {args.output}")


if __name__ == "__main__":
    main()
