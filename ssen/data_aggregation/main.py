from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_FILE = Path(__file__).with_name(
	# "Ground Clearance Confidence [SSEN2025_SHEPD_ALL BLOCKS Terrain Reports_ConfidenceCheck EXPT].csv"
	"Ground Clearance Confidence (1).csv"
)
# VALUE_COLUMN = "Ground Clearance Environments Item Xy Shift Distance Norm"
VALUE_COLUMN="Planes DIFF"
ID_COLUMN = "Global ID"
MAX_VALUE = 10
BUCKET_MODE = "log"  # "log" or "constant"
INITIAL_BUCKET_SIZE = 0.1
CONSTANT_BUCKET_SIZE = 0.1
Y_LOG_SCALE = True
SURFACE_COLOR = "#fcfcfb"
INK_COLOR = "#0b0b0b"
SIGN_COLORS = {"> 0": "#2a78d6", "= 0": "#c3c2b7", "< 0": "#e34948"}


def make_log_bucket_edges(max_value: float) -> np.ndarray:
	positive_edges = [0.0]
	initial_decade = int(np.floor(np.log10(INITIAL_BUCKET_SIZE)))
	decade = initial_decade
	while positive_edges[-1] < max_value:
		step = 10**decade
		start = 0.0 if decade == initial_decade else 10**decade
		precision = max(0, -decade) + 2
		first_offset = 1 if decade == initial_decade else 0
		last_offset = 11 if decade == initial_decade else 10
		if decade != initial_decade:
			first_offset = 1
		positive_edges.extend(round(start + step * i, precision) for i in range(first_offset, last_offset))
		decade += 1
	positive_edges = np.array(positive_edges)
	return np.concatenate((-positive_edges[1:][::-1], positive_edges))


def make_constant_bucket_edges(min_value: float, max_value: float) -> np.ndarray:
	if CONSTANT_BUCKET_SIZE <= 0:
		raise ValueError("CONSTANT_BUCKET_SIZE must be greater than 0.")

	start = np.floor(min_value / CONSTANT_BUCKET_SIZE) * CONSTANT_BUCKET_SIZE
	end = np.ceil(max_value / CONSTANT_BUCKET_SIZE) * CONSTANT_BUCKET_SIZE
	return np.arange(start, end + CONSTANT_BUCKET_SIZE / 2, CONSTANT_BUCKET_SIZE)


def format_bucket_value(value: float, step: float) -> str:
	decimals = 0
	while decimals < 10 and not np.isclose(step * 10**decimals, round(step * 10**decimals)):
		decimals += 1
	formatted = f"{value:.{decimals}f}"
	return formatted if decimals == 0 else formatted.rstrip("0").rstrip(".")


def format_bucket_label(index: int, edges: np.ndarray, zero_index: int, step: float | None) -> str:
	if index == zero_index:
		return "[0, 0]"

	edge_index = index if index < zero_index else index - 1
	bucket_step = step or edges[edge_index + 1] - edges[edge_index]
	left_bracket = "[" if edge_index < zero_index else "("
	return (
		f"{left_bracket}{format_bucket_value(edges[edge_index], bucket_step)}, "
		f"{format_bucket_value(edges[edge_index + 1], bucket_step)})"
	)


def main() -> None:
	data = pd.read_csv(INPUT_FILE, usecols=[ID_COLUMN, VALUE_COLUMN])
	data[VALUE_COLUMN] = pd.to_numeric(data[VALUE_COLUMN], errors="coerce")

	valid = data[
		data[VALUE_COLUMN].notna()
		& (data[VALUE_COLUMN] >= -MAX_VALUE)
		& (data[VALUE_COLUMN] <= MAX_VALUE)
	].copy()
	if BUCKET_MODE == "log":
		bucket_edges = make_log_bucket_edges(MAX_VALUE)
	elif BUCKET_MODE == "constant":
		bucket_edges = make_constant_bucket_edges(-MAX_VALUE, MAX_VALUE)
	else:
		raise ValueError("BUCKET_MODE must be 'log' or 'constant'.")

	zero_edge_index = int(np.searchsorted(bucket_edges, 0.0))
	valid["Bucket index"] = np.searchsorted(bucket_edges, valid[VALUE_COLUMN], side="right") - 1
	positive_values = valid[VALUE_COLUMN] > 0
	valid.loc[positive_values, "Bucket index"] += 1
	valid.loc[valid[VALUE_COLUMN] == 0, "Bucket index"] = zero_edge_index
	valid["Bucket index"] = valid["Bucket index"].clip(upper=len(bucket_edges) - 1)

	bucket_counts = (
		valid.groupby("Bucket index")
		.size()
			.reindex(range(len(bucket_edges)), fill_value=0)
		.rename("Count")
		.reset_index()
	)
	bucket_counts["Bucket (m)"] = bucket_counts["Bucket index"].map(
		lambda index: 0 if index == zero_edge_index else bucket_edges[index if index < zero_edge_index else index - 1]
	)
	constant_step = CONSTANT_BUCKET_SIZE if BUCKET_MODE == "constant" else None
	bucket_counts["Bucket"] = bucket_counts["Bucket index"].map(
		lambda index: format_bucket_label(index, bucket_edges, zero_edge_index, constant_step)
	)
	bucket_counts = bucket_counts[["Bucket", "Bucket (m)", "Count"]]

	output_table = INPUT_FILE.with_name(f"{VALUE_COLUMN}_shift_buckets.csv")
	output_plot = INPUT_FILE.with_name(f"{VALUE_COLUMN}_shift_buckets.png")
	output_pie = INPUT_FILE.with_name(f"{VALUE_COLUMN}_sign_breakdown.png")
	bucket_counts.to_csv(output_table, index=False)

	plt.figure(figsize=(12, 6))
	plt.bar(bucket_counts["Bucket"], bucket_counts["Count"], color="#2878b5")        
	plt.title(f"{'Logarithmic ' if Y_LOG_SCALE else ''}{VALUE_COLUMN}")
	plt.xlabel(f"{BUCKET_MODE.capitalize()} bucket (m)")
	plt.ylabel("Occurrence count")
	if Y_LOG_SCALE:
		plt.yscale("log")
	plt.xticks(rotation=45, ha="right")
	plt.tight_layout()
	plt.savefig(output_plot, dpi=150)
	plt.close()

	sign_counts = pd.Series(
		{
			"> 0": int((valid[VALUE_COLUMN] > 0).sum()),
			"= 0": int((valid[VALUE_COLUMN] == 0).sum()),
			"< 0": int((valid[VALUE_COLUMN] < 0).sum()),
		}
	)
	drawn_signs = sign_counts[sign_counts > 0]

	figure, axes = plt.subplots(figsize=(7, 7))
	figure.patch.set_facecolor(SURFACE_COLOR)
	axes.set_facecolor(SURFACE_COLOR)
	axes.pie(
		drawn_signs,
		labels=[
			f"{sign}\n{count:,} ({count / len(valid):.1%})" for sign, count in drawn_signs.items()
		],
		colors=[SIGN_COLORS[sign] for sign in drawn_signs.index],
		startangle=90,
		counterclock=False,
		labeldistance=1.08,
		textprops={"color": INK_COLOR, "fontsize": 11},
		wedgeprops={"edgecolor": SURFACE_COLOR, "linewidth": 2},
	)
	axes.set_title(f"{VALUE_COLUMN} sign breakdown (n = {len(valid):,})", color=INK_COLOR)
	axes.axis("equal")
	plt.tight_layout()
	plt.savefig(output_pie, dpi=150, facecolor=SURFACE_COLOR)
	plt.close()

	print(f"Rows read: {len(data):,}")
	print(f"Rows included (-{MAX_VALUE:,} to {MAX_VALUE:,} m): {len(valid):,}")
	print(f"Rows rejected or missing: {len(data) - len(valid):,}")
	print("\nBucket counts:")
	print(bucket_counts[["Bucket", "Count"]].to_string(index=False))
	print("\nSign breakdown:")
	for sign, count in sign_counts.items():
		print(f"{sign:>4}: {count:,} ({count / len(valid):.1%})")
	print(f"\nTable written to: {output_table}")
	print(f"Plot written to: {output_plot}")
	print(f"Pie chart written to: {output_pie}")


if __name__ == "__main__":
	main()
