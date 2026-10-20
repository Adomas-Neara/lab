from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


OLD_COLUMN = "Ground Clearance Plane Violation"
REQUIRED_COLUMN = "Required Ground Clearance"
PLANE_COLUMN = "Smallest Ground Plane 10"
IDENTITY_COLUMNS = ["Global ID", "Asset Number", "Block Name", "Span Voltage"]
DEFAULT_INPUT = "conf09-21.csv"
TRANSITIONS = [(True, True), (True, False), (False, True), (False, False)]
SAMPLE_ROWS = 10


def compare(input_path: Path) -> pd.DataFrame:
	frame = pd.read_csv(input_path, usecols=IDENTITY_COLUMNS + [OLD_COLUMN, REQUIRED_COLUMN, PLANE_COLUMN], low_memory=False)
	frame["Old"] = frame[OLD_COLUMN].astype("boolean")
	frame["Margin"] = pd.to_numeric(frame[REQUIRED_COLUMN], errors="coerce") - pd.to_numeric(frame[PLANE_COLUMN], errors="coerce")
	frame["New"] = (frame["Margin"] > 0).astype("boolean").mask(frame["Margin"].isna())
	return frame


def print_report(frame: pd.DataFrame) -> None:
	total = len(frame)
	sections = {(old, new): frame[(frame["Old"] == old) & (frame["New"] == new)] for old, new in TRANSITIONS}
	changed = sum(len(sections[key]) for key in [(True, False), (False, True)])

	print(f"Rows: {total:,}")
	print(f"Old rule: {OLD_COLUMN}")
	print(f"New rule: {REQUIRED_COLUMN} - {PLANE_COLUMN} > 0")
	if (invalid := int(frame["New"].isna().sum())):
		print(f"Rows with no new value (missing input): {invalid:,}")

	print("\n=== Totals ===")
	print(f"{'':10}{'TRUE':>12}{'FALSE':>12}")
	for name, column in [("Before", "Old"), ("After", "New")]:
		trues, falses = int((frame[column] == True).sum()), int((frame[column] == False).sum())
		print(f"{name:10}{trues:>12,}{falses:>12,}   ({trues / total:.2%} / {falses / total:.2%})")
	old_trues, new_trues = int((frame["Old"] == True).sum()), int((frame["New"] == True).sum())
	print(f"{'Net':10}{new_trues - old_trues:>+12,}{old_trues - new_trues:>+12,}")

	print(f"\nChanged: {changed:,} rows ({changed / total:.2%}) - {len(sections[(True, False)]):,} TRUE->FALSE, {len(sections[(False, True)]):,} FALSE->TRUE")
	print(f"TRUE rows that flipped: {len(sections[(True, False)]) / old_trues:.2%} of the {old_trues:,} old TRUEs")
	print(f"FALSE rows that flipped: {len(sections[(False, True)]) / (total - old_trues):.2%} of the {total - old_trues:,} old FALSEs")

	pd.set_option("display.width", 250, "display.max_colwidth", 70)
	for (old, new), section in sections.items():
		print(f"\n=== {str(old).upper()} -> {str(new).upper()} : {len(section):,} rows ({len(section) / total:.2%}) ===")
		if section.empty:
			continue
		print(f"Margin ({REQUIRED_COLUMN} - {PLANE_COLUMN}): min {section['Margin'].min():.2f}, median {section['Margin'].median():.2f}, max {section['Margin'].max():.2f}")
		if old != new:
			print(section.reindex(section["Margin"].abs().sort_values(ascending=False).index)[IDENTITY_COLUMNS + [PLANE_COLUMN, "Margin"]].head(SAMPLE_ROWS).to_string(index=False))


def main() -> None:
	parser = argparse.ArgumentParser(description="Compare the stored ground-clearance plane violation flag with the required-minus-plane rule.")
	parser.add_argument("input", type=Path, nargs="?", default=Path(__file__).parent / DEFAULT_INPUT, help="CSV containing the violation flag and both clearance fields")
	parser.add_argument("--output", type=Path, default=None, help="Optional CSV of the rows that changed")
	args = parser.parse_args()

	frame = compare(args.input)
	print_report(frame)
	if args.output:
		frame[frame["Old"] != frame["New"]].to_csv(args.output, index=False)
		print(f"\nChanged rows: {args.output}")


if __name__ == "__main__":
	main()
