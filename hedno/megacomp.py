from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


EPSILON = 0.01
BOOLS = {"true": True, "false": False}

ID_FIELD_NAME = "ID"


def field_type(values: pd.Series) -> str | None:
	values = values.dropna()
	if values.empty:
		return None
	if values.str.lower().isin(BOOLS.keys()).all():
		return "boolean"
	numbers = pd.to_numeric(values, errors="coerce")
	if numbers.isna().any():
		return "string"
	return "real" if values.str.contains(r"[.eE]").any() else "int"


def parse(values: pd.Series, kind: str) -> pd.Series:
	if kind == "boolean":
		return values.str.lower().map(BOOLS)
	if kind in ("int", "real"):
		return pd.to_numeric(values, errors="coerce")
	return values


def compare(a: pd.Series, b: pd.Series, kind: str) -> pd.Series:
	status = pd.Series("", index=a.index, dtype=object)
	if kind == "boolean":
		status[a.eq(b)] = "unchanged"
		status[a.eq(True) & b.eq(False)] = "true -> false"
		status[a.eq(False) & b.eq(True)] = "false -> true"
	elif kind in ("int", "real"):
		tolerance = EPSILON if kind == "real" else 0
		status[(a - b).abs().le(tolerance)] = "="
		status[(b - a).gt(tolerance)] = "<"
		status[(a - b).gt(tolerance)] = ">"
	else:
		status[a.eq(b)] = "="
		status[a.notna() & b.notna() & a.ne(b)] = "!="
	status[a.isna() != b.isna()] = "null_mismatch"
	return status


def load(path: Path, key: str | None) -> pd.DataFrame:
	data = pd.read_csv(path, dtype=str, keep_default_na=False).replace("", None)
	return data.drop_duplicates(subset=key).set_index(key) if key else data


def main() -> None:
	parser = argparse.ArgumentParser(description="Field-by-field diff of two report CSVs.")
	parser.add_argument("a", type=Path)
	parser.add_argument("b", type=Path)
	parser.add_argument("--key", default=ID_FIELD_NAME, help="column used to match rows; falls back to row order if missing")
	parser.add_argument("--out", type=Path, help="defaults to <a>_vs_<b>.csv next to a")
	args = parser.parse_args()

	header_a = pd.read_csv(args.a, nrows=0).columns
	header_b = pd.read_csv(args.b, nrows=0).columns
	key = args.key if args.key in header_a and args.key in header_b else None
	a, b = load(args.a, key), load(args.b, key)
	message = [f"A: {args.a.name} ({len(a):,} rows)", f"B: {args.b.name} ({len(b):,} rows)", f"Rows matched by: {key or 'row order'}"]

	only_a = [f for f in a.columns if f not in b.columns]
	only_b = [f for f in b.columns if f not in a.columns]
	if only_a or only_b:
		message.append("\nFIELD MISMATCH - rejected from output:")
		message += [f"  only in A: {f}" for f in only_a] + [f"  only in B: {f}" for f in only_b]

	shared = a.index.intersection(b.index)
	if len(shared) < max(len(a), len(b)):
		message.append(f"\nRows only in A: {len(a.index.difference(shared)):,}, only in B: {len(b.index.difference(shared)):,} (excluded)")
	a, b = a.loc[shared], b.loc[shared]

	output = pd.DataFrame(index=a.index)
	type_mismatches = []
	summary = []
	for field in [f for f in a.columns if f in b.columns]:
		kind_a, kind_b = field_type(a[field]), field_type(b[field])
		if kind_a and kind_b and kind_a != kind_b:
			type_mismatches.append(f"  {field}: A={kind_a}, B={kind_b}")
			continue
		kind = kind_a or kind_b or "string"
		output[field] = compare(parse(a[field], kind), parse(b[field], kind), kind)
		counts = output[field].replace("", "both null").value_counts()
		summary.append(f"  {field} [{kind}]: " + ", ".join(f"'{k}': {v:,}" for k, v in counts.items()))

	if type_mismatches:
		message += ["\nTYPE MISMATCH - rejected from output:"] + type_mismatches
	message += ["\nCompared fields:"] + summary

	out = args.out or args.a.with_name(f"{args.a.stem}_vs_{args.b.stem}.csv")
	output.rename_axis(key or "row").reset_index().to_csv(out, index=False)
	out.with_suffix(".txt").write_text("\n".join(message), encoding="utf-8")
	print("\n".join(message))
	print(f"\nWrote {out}")


if __name__ == "__main__":
	main()
