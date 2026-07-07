"""Extract the PhilHealth Annex B procedure case rate table into a CSV.

Usage:
    python scrape_case_rates.py --input AnnexB-ListofProcedureCaseRates.pdf --output ../data/procedure_case_rates.csv
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADER_FIRST_COLUMN = "RVS Code"


def clean_procedure(description: str) -> str:
    """Collapse a wrapped, multi-line description into a single line."""
    return re.sub(r"\s+", " ", description).strip()


def clean_case_rate(value: str) -> str:
    """Normalize a case rate string (e.g. '1 0,920.00') into 'NNNN.NN'."""
    digits = re.sub(r"[\s,]", "", value)
    return f"{float(digits):.2f}"


def extract_rows(pdf_path: Path) -> list[dict]:
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    code, description, case_rate = row[0], row[1], row[2]
                    if not code or code == HEADER_FIRST_COLUMN:
                        continue
                    if not description or not case_rate:
                        continue
                    rows.append(
                        {
                            "rvs_code": code.strip(),
                            "procedure": clean_procedure(description),
                            "case_rate": clean_case_rate(case_rate),
                        }
                    )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Path to the Annex B PDF")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "procedure_case_rates.csv",
        help="Path to write the output CSV",
    )
    args = parser.parse_args()

    rows = extract_rows(args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["rvs_code", "procedure", "case_rate"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
