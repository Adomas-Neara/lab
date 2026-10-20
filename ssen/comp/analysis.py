from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


GROUND_PLANE = "Ground Plane Distance"
SMALLEST_PLANE = "Smallest Ground Plane 10"
GROUND_ERROR = "Ground Plane Error"
SMALLEST_ERROR = "Smallest Plane Error"
REFERENCE = "Validated Height"
WINNER = "More Accurate Field"
GROUND_WINNER = "Ground Clearance Environments Item Ground Plane Distance Distance"
SMALLEST_WINNER = "Smallest Ground Plane 10"


def default_input_path() -> Path:
	base_path = Path(__file__).parent
	preferred_path = base_path / (
		"Ground Clearance Confidence [SSEN2025_SEPD_ALL BLOCKS Terrain Reports_ConfidenceCheck EXPT]_comparison_results.csv"
	)
	if preferred_path.exists():
		return preferred_path
	comparison_files = sorted(base_path.glob("*_comparison_results.csv"))
	if comparison_files:
		return comparison_files[0]
	return base_path / "comparison_results.csv"


def load_analysis_data(input_path: Path) -> pd.DataFrame:
	data = pd.read_csv(input_path)
	for column in [REFERENCE, GROUND_PLANE, SMALLEST_PLANE, GROUND_ERROR, SMALLEST_ERROR]:
		data[column] = pd.to_numeric(data[column], errors="coerce")

	matched = data["Match Status"].isin(["matched", "multiple matches"])
	data["Ground Plane Signed Error"] = data[GROUND_PLANE] - data[REFERENCE]
	data["Smallest Plane Signed Error"] = data[SMALLEST_PLANE] - data[REFERENCE]
	data["Ground Plane Absolute Error"] = data[GROUND_ERROR].abs()
	data["Smallest Plane Absolute Error"] = data[SMALLEST_ERROR].abs()
	data["Ground Plane Squared Error"] = data["Ground Plane Signed Error"] ** 2
	data["Smallest Plane Squared Error"] = data["Smallest Plane Signed Error"] ** 2
	data["Analysis Status"] = "included" 
	data.loc[~matched, "Analysis Status"] = "excluded: " + data.loc[~matched, "Match Status"].astype(str)
	return data


def summarize(data: pd.DataFrame) -> pd.DataFrame:
	comparable = data[data[WINNER].isin([GROUND_WINNER, SMALLEST_WINNER, "tie"])]
	rows: list[dict[str, object]] = []
	for label, error_column, signed_column in [
		(GROUND_PLANE, "Ground Plane Absolute Error", "Ground Plane Signed Error"),
		(SMALLEST_PLANE, "Smallest Plane Absolute Error", "Smallest Plane Signed Error"),
	]:
		errors = data[error_column].dropna()
		signed_errors = data[signed_column].dropna()
		winner_label = GROUND_WINNER if label == GROUND_PLANE else SMALLEST_WINNER
		rows.append(
			{
				"Field": label,
				"Rows compared": len(errors),
				"Wins": int((data[WINNER] == winner_label).sum()),
				"Mean absolute error": errors.mean(),
				"Median absolute error": errors.median(),
				"RMSE": (signed_errors**2).mean() ** 0.5,
				"Mean signed error": signed_errors.mean(),
				"Within 0.10": int((errors <= 0.10).sum()),
				"Within 0.25": int((errors <= 0.25).sum()),
				"Within 0.50": int((errors <= 0.50).sum()),
				"90th percentile absolute error": errors.quantile(0.90),
				"Maximum absolute error": errors.max(),
			}
		)

	rows.extend(
		[
			{"Field": "Ties", "Wins": int((data[WINNER] == "tie").sum())},
			{"Field": "Neither value available", "Rows compared": int((data[WINNER] == "neither").sum())},
			{"Field": "Unmatched", "Rows compared": int((data["Match Status"] == "unmatched").sum())},
		]
	)
	return pd.DataFrame(rows)


def make_chart(data: pd.DataFrame, chart_path: Path) -> None:
	comparable = data[data[WINNER].isin([GROUND_WINNER, SMALLEST_WINNER, "tie"])]
	figure, axes = plt.subplots(2, 2, figsize=(14, 10))

	axes[0, 0].hist(
		comparable["Ground Plane Absolute Error"].dropna(), bins=40, alpha=0.65, label=GROUND_PLANE
	)
	axes[0, 0].hist(
		comparable["Smallest Plane Absolute Error"].dropna(), bins=40, alpha=0.65, label=SMALLEST_PLANE
	)
	axes[0, 0].set_title("Absolute error distribution")
	axes[0, 0].set_xlabel("Absolute error")
	axes[0, 0].set_ylabel("Rows")
	axes[0, 0].legend()

	axes[0, 1].boxplot(
		[
			comparable["Ground Plane Absolute Error"].dropna(),
			comparable["Smallest Plane Absolute Error"].dropna(),
		],
		tick_labels=["Ground Plane", "Smallest Plane"],
		showfliers=False,
	)
	axes[0, 1].set_title("Absolute error spread")
	axes[0, 1].set_ylabel("Absolute error")

	axes[1, 0].scatter(
		comparable[REFERENCE], comparable[GROUND_PLANE], s=8, alpha=0.25, label=GROUND_PLANE
	)
	axes[1, 0].scatter(
		comparable[REFERENCE], comparable[SMALLEST_PLANE], s=8, alpha=0.25, label=SMALLEST_PLANE
	)
	axis_limits = [comparable[REFERENCE].min(), comparable[REFERENCE].max()]
	axes[1, 0].plot(axis_limits, axis_limits, "k--", linewidth=1, label="Reference")
	axes[1, 0].set_title("Measurements vs validated height")
	axes[1, 0].set_xlabel("Validated height")
	axes[1, 0].set_ylabel("Computed measurement")
	axes[1, 0].legend()

	winner_counts = data[WINNER].value_counts().reindex([GROUND_WINNER, SMALLEST_WINNER, "tie", "neither"], fill_value=0)
	short_labels = ["Ground Plane", "Smallest Plane", "Tie", "Neither"]
	axes[1, 1].bar(short_labels, winner_counts.values, color=["#2f6690", "#f28e2b", "#8c8c8c", "#c9c9c9"])
	axes[1, 1].set_title("Per-row comparison result")
	axes[1, 1].set_ylabel("Rows")
	axes[1, 1].tick_params(axis="x", rotation=20)

	figure.suptitle("Ground-clearance comparison analysis")
	figure.tight_layout()
	figure.savefig(chart_path, dpi=160)
	plt.close(figure)


def main() -> None:
	default_input = default_input_path()
	parser = argparse.ArgumentParser(description="Analyze a computed ground-clearance comparison CSV.")
	parser.add_argument("input", type=Path, nargs="?", default=default_input, help="Computed comparison CSV")
	parser.add_argument("--details", type=Path, default=Path("detailed_comparison_analysis.csv"), help="Per-row analysis CSV")
	parser.add_argument("--summary", type=Path, default=Path("comparison_summary.csv"), help="Summary statistics CSV")
	parser.add_argument("--chart", type=Path, default=Path("comparison_analysis.png"), help="Chart image")
	args = parser.parse_args()

	data = load_analysis_data(args.input)
	summary = summarize(data)
	data.to_csv(args.details, index=False)
	summary.to_csv(args.summary, index=False)
	make_chart(data, args.chart)

	print(f"Input: {args.input}")
	print(f"Detailed analysis: {args.details}")
	print(f"Summary: {args.summary}")
	print(f"Chart: {args.chart}")
	print(summary.to_string(index=False))


if __name__ == "__main__":
	main()
