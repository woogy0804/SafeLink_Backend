"""Remove one verified, position-for-position repeated half from a CSV dataset."""

import argparse
import csv
import os
import tempfile
from pathlib import Path


def remove_repeated_half(input_path: Path, output_path: Path) -> int:
    with input_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError("Dataset has no header")
        rows = list(reader)

    if not rows or len(rows) % 2:
        raise ValueError("Dataset does not contain two equal-sized halves")
    comparison_columns = [name for name in reader.fieldnames if name != "index"]
    half = len(rows) // 2
    mismatch_count = sum(
        any(rows[index][name] != rows[index + half][name] for name in comparison_columns)
        for index in range(half)
    )
    if mismatch_count:
        raise ValueError(
            f"Dataset halves are not exact repeats: {mismatch_count} mismatched rows"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(rows[:half])
        Path(temporary_name).replace(output_path)
    except Exception:
        try:
            Path(temporary_name).unlink()
        except FileNotFoundError:
            pass
        raise
    return half


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    count = remove_repeated_half(arguments.input, arguments.output)
    print(f"Wrote {count:,} rows to {arguments.output}")


if __name__ == "__main__":
    main()
