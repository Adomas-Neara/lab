from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


REFERENCE_COLUMNS = [
	"Assetnum", 
	"Validated Height"
]
CONFIDENCE_COLUMNS = [
	"Global ID",
	"Ground Clearance Environments Item Ground Plane Distance Distance",
	"Smallest Ground Plane 10",
]
GROUND_PLANE_COLUMN = CONFIDENCE_COLUMNS[1]
SMALLEST_PLANE_COLUMN = CONFIDENCE_COLUMNS[2]
DEFAULT_REFERENCE = "RealWorldRef.csv"
DEFAULT_CONFIDENCE = "Ground Clearance Confidence [SSEN2025_SEPD_ALL BLOCKS Terrain Reports_ConfidenceCheck EXPT].csv"


def default_paths() -> tuple[Path, Path, Path]:
	base_path = Path(__file__).parent
	reference_path = base_path / DEFAULT_REFERENCE
	confidence_path = base_path / DEFAULT_CONFIDENCE
	output_path = base_path / f"{confidence_path.stem}_comparison_results.csv"
	return reference_path, confidence_path, output_path


def compare_reports(reference_path: Path, confidence_path: Path) -> tuple[pd.DataFrame, dict[str, int | float | str]]:
	reference = pd.read_csv(reference_path, usecols=REFERENCE_COLUMNS, dtype={"Assetnum": "string"})
	confidence = pd.read_csv(
		confidence_path,
		usecols=CONFIDENCE_COLUMNS,
		dtype={"Global ID": "string"},
	)

	reference["Assetnum"] = reference["Assetnum"].fillna("").str.strip()
	confidence["Global ID"] = confidence["Global ID"].fillna("")
	reference["Validated Height"] = pd.to_numeric(reference["Validated Height"], errors="coerce")
	confidence[GROUND_PLANE_COLUMN] = pd.to_numeric(confidence[GROUND_PLANE_COLUMN], errors="coerce")
	confidence[SMALLEST_PLANE_COLUMN] = pd.to_numeric(confidence[SMALLEST_PLANE_COLUMN], errors="coerce")

	assetnums = {assetnum for assetnum in reference["Assetnum"] if assetnum}
	matches_by_assetnum: dict[str, list[int]] = {assetnum: [] for assetnum in assetnums}
	for confidence_index, global_id in confidence["Global ID"].items():
		for assetnum in set(re.findall(r"\d+", global_id)) & assetnums:
			matches_by_assetnum[assetnum].append(confidence_index)

	results: list[dict[str, object]] = []
	for _, reference_row in reference.iterrows():
		assetnum = reference_row["Assetnum"]
		match_indices = matches_by_assetnum.get(assetnum, [])
		matches = confidence.loc[match_indices]

		if matches.empty:
			results.append(
				{
					"Assetnum": assetnum,
					"Validated Height": reference_row["Validated Height"],
					"Match Status": "unmatched",
					"Matched Global ID": pd.NA,
					"Ground Plane Distance": pd.NA,
					"Smallest Ground Plane 10": pd.NA,
					"Ground Plane Error": pd.NA,
					"Smallest Plane Error": pd.NA,
					"More Accurate Field": "unmatched",
				}
			)
			continue

		match = matches.iloc[0]
		validated_height = reference_row["Validated Height"]
		ground_plane = match[GROUND_PLANE_COLUMN]
		smallest_plane = match[SMALLEST_PLANE_COLUMN]
		ground_error = abs(ground_plane - validated_height) if pd.notna(ground_plane) and pd.notna(validated_height) else pd.NA
		smallest_error = abs(smallest_plane - validated_height) if pd.notna(smallest_plane) and pd.notna(validated_height) else pd.NA

		if pd.isna(ground_error) and pd.isna(smallest_error):
			winner = "neither"
		elif pd.isna(ground_error):
			winner = "Smallest Ground Plane 10"
		elif pd.isna(smallest_error):
			winner = GROUND_PLANE_COLUMN
		elif ground_error < smallest_error:
			winner = GROUND_PLANE_COLUMN
		elif smallest_error < ground_error:
			winner = "Smallest Ground Plane 10"
		else:
			winner = "tie"

		results.append(
			{
				"Assetnum": assetnum,
				"Validated Height": validated_height,
				"Match Status": "multiple matches" if len(matches) > 1 else "matched",
				"Matched Global ID": match["Global ID"],
				"Ground Plane Distance": ground_plane,
				"Smallest Ground Plane 10": smallest_plane,
				"Ground Plane Error": ground_error,
				"Smallest Plane Error": smallest_error,
				"More Accurate Field": winner,
			}
		)

	result_frame = pd.DataFrame(results)
	comparable = result_frame[result_frame["More Accurate Field"].isin([GROUND_PLANE_COLUMN, "Smallest Ground Plane 10", "tie"])]
	summary = {
		"reference_rows": len(reference),
		"matched_rows": int(result_frame["Match Status"].isin(["matched", "multiple matches"]).sum()),
		"unmatched_rows": int((result_frame["Match Status"] == "unmatched").sum()),
		"multiple_match_rows": int((result_frame["Match Status"] == "multiple matches").sum()),
		"comparable_rows": len(comparable),
		"ground_plane_wins": int((result_frame["More Accurate Field"] == GROUND_PLANE_COLUMN).sum()),
		"smallest_plane_wins": int((result_frame["More Accurate Field"] == "Smallest Ground Plane 10").sum()),
		"ties": int((result_frame["More Accurate Field"] == "tie").sum()),
		"neither": int((result_frame["More Accurate Field"] == "neither").sum()),
		"ground_plane_mae": float(result_frame["Ground Plane Error"].mean()),
		"smallest_plane_mae": float(result_frame["Smallest Plane Error"].mean()),
	}
	if summary["ground_plane_mae"] < summary["smallest_plane_mae"]:
		summary["overall_winner"] = GROUND_PLANE_COLUMN
	elif summary["smallest_plane_mae"] < summary["ground_plane_mae"]:
		summary["overall_winner"] = "Smallest Ground Plane 10"
	else:
		summary["overall_winner"] = "tie"
	return result_frame, summary


def main() -> None:
	default_reference, default_confidence, default_output = default_paths()
	parser = argparse.ArgumentParser(description="Compare ground-clearance measurements with validated heights.")
	parser.add_argument("reference", type=Path, nargs="?", default=default_reference, help="CSV containing Assetnum and Validated Height")
	parser.add_argument("confidence", type=Path, nargs="?", default=default_confidence, help="CSV containing Global ID and the two measurements")
	parser.add_argument("--output", type=Path, default=default_output, help="Detailed output CSV")
	args = parser.parse_args()

	results, summary = compare_reports(args.reference, args.confidence)
	results.to_csv(args.output, index=False)
	print(f"Detailed results: {args.output}")
	print(f"Rows in reference report: {summary['reference_rows']}")
	print(f"Matched rows: {summary['matched_rows']}")
	print(f"Unmatched rows: {summary['unmatched_rows']}")
	print(f"Rows with multiple matches: {summary['multiple_match_rows']}")
	print(f"Comparable rows: {summary['comparable_rows']}")
	print(f"Ground Plane Distance wins: {summary['ground_plane_wins']}")
	print(f"Smallest Ground Plane 10 wins: {summary['smallest_plane_wins']}")
	print(f"Ties: {summary['ties']}")
	print(f"Neither value available: {summary['neither']}")
	print(f"Mean absolute error, Ground Plane Distance: {summary['ground_plane_mae']:.6f}")
	print(f"Mean absolute error, Smallest Ground Plane 10: {summary['smallest_plane_mae']:.6f}")


if __name__ == "__main__":
	main()
