"""Write a compact markdown data-quality report for generated tables."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"


def report() -> str:
    lines = ["# Synthetic data quality report", "", "> Demo data only; missingness and outliers are intentionally injected.", "", "| Table | Rows | Columns | Missing cells | Duplicate rows |", "|---|---:|---:|---:|---:|"]
    for path in sorted(DATA.glob("*.csv")):
        df = pd.read_csv(path)
        lines.append(f"| `{path.name}` | {len(df):,} | {len(df.columns)} | {int(df.isna().sum().sum()):,} | {int(df.duplicated().sum()):,} |")
    lines += ["", "## Checks", "", "- Identifiers are generated and do not contain resident names, phone numbers or addresses.", "- Pocket coordinates are plausible demo locations around the MMR; they are not settlement boundaries.", "- Numeric missingness is expected at roughly 3–8% in pocket and service tables.", "- Replace this report with source-specific validation before any policy use.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    if not DATA.exists() or not list(DATA.glob("*.csv")):
        from generate_data import generate
        generate()
    out = ROOT / "data" / "processed" / "data_quality_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report(), encoding="utf-8")
    print(out)
