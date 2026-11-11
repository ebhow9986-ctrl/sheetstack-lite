from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sheetstack_lite import __version__
from sheetstack_lite.clean import clean_frame
from sheetstack_lite.io import collect_inputs, read_table, write_table
from sheetstack_lite.merge import merge_tables


def cmd_merge(args: argparse.Namespace) -> int:
    paths = collect_inputs(args.inputs)
    merged, logs = merge_tables(
        paths,
        add_source=not args.no_source,
        encoding=args.encoding,
        normalize_headers=args.normalize_headers,
    )
    write_table(merged, Path(args.output))
    print(f"Merged {len(paths)} file(s), {len(merged)} rows, {merged.shape[1]} columns")
    for log in logs:
        print(f"  - {log['file']}: {log['rows']} rows / encoding {log['encoding']}")
    print(f"Wrote {args.output}")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    df, used = read_table(Path(args.input), args.encoding)
    date_cols = [c.strip() for c in args.date_cols.split(",") if c.strip()] or None
    dedupe_cols = [c.strip() for c in args.dedupe_cols.split(",") if c.strip()] or None
    cleaned, report, _ = clean_frame(df, date_cols=date_cols, dedupe_cols=dedupe_cols, dayfirst=args.dayfirst)
    write_table(cleaned, Path(args.output))
    print(
        f"Cleaned {report['input_rows']} rows → {report['output_rows']} rows "
        f"(empty {report['empty_rows_dropped']}, duplicates {report['duplicates_removed']})"
    )
    print(f"Detected encoding: {used}")
    print(f"Wrote {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sheetstack-lite",
        description="Sheetstack Lite: merge and clean CSV/Excel files in memory.",
    )
    parser.add_argument("--version", action="version", version=f"Sheetstack Lite {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_merge = sub.add_parser("merge", help="Merge CSV/Excel files")
    p_merge.add_argument("inputs", nargs="+")
    p_merge.add_argument("-o", "--output", required=True)
    p_merge.add_argument("--no-source", action="store_true")
    p_merge.add_argument("--normalize-headers", action="store_true")
    p_merge.add_argument("--encoding", default="auto")
    p_merge.set_defaults(func=cmd_merge)

    p_clean = sub.add_parser("clean", help="Trim, drop empty rows, normalize dates, dedupe")
    p_clean.add_argument("input")
    p_clean.add_argument("-o", "--output", required=True)
    p_clean.add_argument("--date-cols", default="")
    p_clean.add_argument("--dedupe-cols", default="")
    p_clean.add_argument("--encoding", default="auto")
    p_clean.add_argument("--dayfirst", action="store_true")
    p_clean.set_defaults(func=cmd_clean)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
