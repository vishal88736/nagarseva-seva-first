"""Run independent source stages and continue after any source-specific failure."""
import argparse
import subprocess
import sys
from data_common import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Recheck sources while preserving content-addressed originals")
    args = parser.parse_args()
    failures = []
    sources = ["inspect_sra_layers.py", "ingest_sra.py", "ingest_sra_projects.py", "ingest_osm.py", "ingest_census.py"]
    stages = sources + ["prepare_demo_data.py", "prepare_real_data.py", "validate_datasets.py"]
    for script in stages:
        command = [sys.executable, str(ROOT / "scripts" / script)]
        if args.refresh and script in sources:
            command.append("--refresh")
        try:
            result = subprocess.run(command, cwd=ROOT, timeout=600)
            if result.returncode:
                failures.append({"stage": script, "exit_code": result.returncode})
        except subprocess.TimeoutExpired:
            failures.append({"stage": script, "error": "stage exceeded ten-minute acquisition limit"})
    if failures:
        print("Stage failures:", failures)
        raise SystemExit(1)
    print("Pipeline finished. Source availability and acquisition failures are in research/dataset_inventory.csv and data/metadata/.")


if __name__ == "__main__":
    main()
