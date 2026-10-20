from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


VERTICAL_COLUMN = "Plane Distance Out Of Smallest 10 Vertical"
PLANE_COLUMN = "Smallest Ground Plane 10"
IDENTITY_COLUMNS = ["Global ID", "Asset Number", "Block Name", "Span Voltage"]
DEFAULT_INPUT = "conf09-21.csv"
TOP_ROWS = 10

SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
CATEGORIES = [
	("< 0", "#2a78d6", None),
	("= 0", "#c3c2b7", None),
	("> 0", "#d03b3b", None),
	("Invalid (one field null)", "#898781", "///"),
]


def categorise(input_path: Path) -> pd.DataFrame:
	frame = pd.read_csv(input_path, usecols=IDENTITY_COLUMNS + [VERTICAL_COLUMN, PLANE_COLUMN], low_memory=False)
	vertical = pd.to_numeric(frame[VERTICAL_COLUMN], errors="coerce")
	plane = pd.to_numeric(frame[PLANE_COLUMN], errors="coerce")
	frame["Difference"] = vertical - plane

	frame["Category"] = pd.Series(pd.NA, index=frame.index, dtype="string")
	frame.loc[frame["Difference"] < 0, "Category"] = "< 0"
	frame.loc[frame["Difference"] == 0, "Category"] = "= 0"
	frame.loc[frame["Difference"] > 0, "Category"] = "> 0"
	frame.loc[vertical.isna() ^ plane.isna(), "Category"] = "Invalid (one field null)"
	return frame


def plot_pie(counts: dict[str, int], output_path: Path) -> None:
	drawn = [(label, colour, hatch, counts[label]) for label, colour, hatch in CATEGORIES if counts[label]]
	total = sum(counts.values())

	figure, axes = plt.subplots(figsize=(7.5, 5.0), facecolor=SURFACE)
	axes.set_facecolor(SURFACE)
	wedges, _, autotexts = axes.pie(
		[count for *_, count in drawn],
		colors=[colour for _, colour, _, _ in drawn],
		startangle=90,
		counterclock=False,
		autopct=lambda share: f"{share:.1f}%" if share >= 3 else "",
		pctdistance=0.72,
		wedgeprops={"edgecolor": SURFACE, "linewidth": 2},
		textprops={"color": PRIMARY_INK, "fontsize": 11, "fontweight": "bold"},
	)
	for wedge, autotext, (_, colour, hatch, _) in zip(wedges, autotexts, drawn):
		if hatch:
			wedge.set_hatch(hatch)
		autotext.set_color(SURFACE if colour in ("#2a78d6", "#d03b3b") else PRIMARY_INK)

	axes.legend(
		handles=[
			plt.matplotlib.patches.Patch(facecolor=colour, hatch=hatch, edgecolor=SURFACE, label=f"{label}  —  {counts[label]:,} ({counts[label] / total:.2%})")
			for label, colour, hatch in CATEGORIES
		],
		loc="center left",
		bbox_to_anchor=(0.98, 0.5),
		frameon=False,
		labelcolor=SECONDARY_INK,
		fontsize=10,
	)
	axes.set_title(
		f"{VERTICAL_COLUMN}\nminus {PLANE_COLUMN}",
		color=PRIMARY_INK,
		fontsize=13,
		loc="left",
	)
	axes.text(-1.35, -1.25, f"{total:,} rows", color=SECONDARY_INK, fontsize=10)
	figure.tight_layout()
	figure.savefig(output_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")


def main() -> None:
	base_path = Path(__file__).parent
	parser = argparse.ArgumentParser(description="Pie chart of the sign of the difference between two ground-plane fields.")
	parser.add_argument("input", type=Path, nargs="?", default=base_path / DEFAULT_INPUT, help="CSV containing both fields")
	parser.add_argument("--output", type=Path, default=base_path / "plane_diff_pie.png", help="Output PNG")
	args = parser.parse_args()

	frame = categorise(args.input)
	counts = {label: int((frame["Category"] == label).sum()) for label, _, _ in CATEGORIES}
	plot_pie(counts, args.output)

	print(f"Chart: {args.output}")
	for label, count in counts.items():
		print(f"{label}: {count:,} ({count / len(frame):.2%})")
	if (unclassified := len(frame) - sum(counts.values())):
		print(f"Both fields null (excluded): {unclassified:,}")

	pd.set_option("display.width", 250, "display.max_colwidth", 70)
	print(f"\nTop {TOP_ROWS} by difference:")
	print(frame.nlargest(TOP_ROWS, "Difference")[IDENTITY_COLUMNS + [VERTICAL_COLUMN, PLANE_COLUMN, "Difference"]].to_string(index=False))


if __name__ == "__main__":
	main()
