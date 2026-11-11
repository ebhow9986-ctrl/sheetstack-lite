# Sheetstack Lite

Free, in-memory **merge** and **clean** for messy CSV and Excel exports.

This lite edition auto-detects common encodings (UTF-8, Windows-1252, Shift-JIS, GBK, and others), can align frequent header aliases, trims whitespace, drops empty rows, normalizes dates to `YYYY-MM-DD`, and deduplicates rows.

It loads each file into memory. If Excel already refuses to open the file, or you need a summary workbook and chunked processing, use the paid toolkit instead:

**Paid edition (chunked reads, split, Excel summary report, one-step pipeline):**  
https://ebhow.gumroad.com/l/sheetstack


## Install

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.10+ is required.

## Examples

```bash
# Merge the sample exports (four encodings)
python sheetstack_lite.py merge samples -o merged.csv --normalize-headers

# Clean a messy list
python sheetstack_lite.py clean samples/customers_messy.csv -o clean.csv --dedupe-cols customer_id --date-cols signup_date
```

Sample files are fictional.

## Lite vs paid

| Feature | Lite (this repo) | Paid ([Gumroad](https://ebhow.gumroad.com/l/sheetstack)) |
| --- | --- | --- |
| Merge + encoding detection | Yes | Yes |
| Clean, dates, dedupe | Yes | Yes |
| Header aliases | Yes | Yes |
| Chunked reads for large CSVs | No | Yes |
| Split into Excel-friendly pieces | No | Yes |
| Excel summary with conditional formatting | No | Yes |
| One-step `run` pipeline | No | Yes |

## Tests

```bash
python tests/test_lite.py
```

## License

MIT. The paid edition has a separate, more restrictive license; this repository does not include the paid source.
