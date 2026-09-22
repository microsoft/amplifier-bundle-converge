"""Export a community publication to a UTF-8 text file."""
import argparse
from pathlib import Path


def export(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    destination.write_text(text[:180], encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    export(args.source, args.destination)
    print("Export complete")
