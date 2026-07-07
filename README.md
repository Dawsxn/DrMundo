# DrMundo

## PhilHealth Procedure Case Rates

[`scraper/scrape_case_rates.py`](scraper/scrape_case_rates.py) extracts the RVS code, procedure
description, and case rate from PhilHealth's "Annex B - List of Procedure Case Rates" PDF into
[`data/procedure_case_rates.csv`](data/procedure_case_rates.csv).

### Usage

```bash
pip install -r scraper/requirements.txt
python scraper/scrape_case_rates.py --input /path/to/AnnexB-ListofProcedureCaseRates.pdf
```

This writes `data/procedure_case_rates.csv` with columns:

- `rvs_code` - RVS/procedure code as printed in the PDF (some are alphanumeric package codes,
  e.g. `MCP01`, and a few chemotherapy codes carry footnote asterisks, e.g. `96408*`)
- `procedure` - procedure description, unwrapped to a single line
- `case_rate` - case rate as a plain decimal number (commas removed)

Health Facility Fee and Professional Fee columns from the source PDF are intentionally omitted.
