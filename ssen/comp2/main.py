from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE = Path(__file__).parent
KEY = "Asset Number"
FIELD = "Ground Clearance Plane Violation"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GREY = "#a9a8a2"


def load(name: str) -> pd.Series:
	data = pd.read_csv(BASE / name, usecols=[KEY, FIELD], dtype=str).dropna(subset=[KEY])
	return data[FIELD].str.upper().eq("TRUE").groupby(data[KEY]).any()


def compare(before: pd.Series, after: pd.Series) -> pd.DataFrame:
	joined = pd.concat({"before": before, "after": after}, axis=1)
	status = pd.Series("unchanged (no violation)", index=joined.index)
	status[joined["before"].eq(True) & joined["after"].eq(True)] = "still violating"
	status[joined["before"].eq(False) & joined["after"].eq(True)] = "new violation"
	status[joined["before"].eq(True) & joined["after"].eq(False)] = "violation cleared"
	status[joined["after"].isna()] = "only in client_main"
	status[joined["before"].isna()] = "only in gp_fallback"
	return joined.assign(status=status)


def style(ax: plt.Axes) -> None:
	ax.set_facecolor(SURFACE)
	for side in ["top", "right", "left"]:
		ax.spines[side].set_visible(False)
	ax.spines["bottom"].set_color(GRID)
	ax.tick_params(colors=INK_2, length=0)
	ax.grid(axis="x", color=GRID, linewidth=0.8)
	ax.set_axisbelow(True)


def plot(joined: pd.DataFrame, path: Path) -> None:
	both = joined.dropna(subset=["before", "after"])
	counts = joined["status"].value_counts()

	fig, (left, right) = plt.subplots(1, 2, figsize=(13, 4.8), facecolor=SURFACE, gridspec_kw={"width_ratios": [1, 1.3]})

	totals = [int(both["before"].sum()), int(both["after"].sum())]
	bars = left.barh(["client_main", "gp_fallback"], totals, color=[BLUE, ORANGE], height=0.5)
	left.bar_label(bars, labels=[f"{v:,}  ({v / len(both):.2%})" for v in totals], padding=6, color=INK, fontsize=10)
	left.invert_yaxis()
	left.set_xlim(0, max(totals) * 1.35)
	left.set_title(f"Violating assets (of {len(both):,} matched)", loc="left", color=INK, fontsize=12, fontweight="bold")
	style(left)

	order = ["still violating", "new violation", "violation cleared", "only in client_main", "only in gp_fallback"]
	values = [int(counts.get(k, 0)) for k in order]
	bars = right.barh(order, values, color=[BLUE, ORANGE, AQUA, GREY, GREY], height=0.6)
	right.bar_label(bars, labels=[f"{v:,}" for v in values], padding=6, color=INK, fontsize=10)
	right.invert_yaxis()
	right.set_xlim(0, max(values) * 1.2)
	changed = int(counts.get("new violation", 0) + counts.get("violation cleared", 0))
	right.set_title(f"Change per asset: {changed:,} flipped ({changed / len(both):.2%})", loc="left", color=INK, fontsize=12, fontweight="bold")
	right.text(0, -0.12, f"{int(counts.get('unchanged (no violation)', 0)):,} assets unchanged with no violation (not shown)", transform=right.transAxes, color=INK_2, fontsize=9)
	style(right)

	fig.suptitle(f"{FIELD}: client_main → gp_fallback", x=0.01, ha="left", color=INK, fontsize=14, fontweight="bold")
	fig.tight_layout()
	fig.savefig(path, dpi=150, facecolor=SURFACE)


def main() -> None:
	joined = compare(load("conf_client_main.csv"), load("conf_gp_fallback.csv"))
	both = joined.dropna(subset=["before", "after"])
	counts = joined["status"].value_counts()

	print(f"Matched assets: {len(both):,}")
	print(f"Violations client_main: {int(both['before'].sum()):,}")
	print(f"Violations gp_fallback:   {int(both['after'].sum()):,}")
	print(f"Net change:             {int(both['after'].sum() - both['before'].sum()):+,}")
	print()
	print(pd.DataFrame({"assets": counts, "share": (counts / len(joined)).map("{:.2%}".format)}).to_string())

	joined.rename_axis(KEY).reset_index().to_csv(BASE / "violation_comparison.csv", index=False)
	plot(joined, BASE / "violation_comparison.png")


if __name__ == "__main__":
	main()
