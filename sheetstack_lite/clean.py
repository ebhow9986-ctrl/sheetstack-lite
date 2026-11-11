"""Trim cells, drop empty rows, normalize dates, and remove duplicates."""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from sheetstack_lite.headers import SOURCE_COLUMN

DATE_CANDIDATES = re.compile(
    r"(date|time|datetime|timestamp|created|下单|成交|日期|时间|日付)",
    re.I,
)
FULLWIDTH = str.maketrans("０１２３４５６７８９．－／　", "0123456789.-/ ")


def to_str(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def strip_cells(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    for col in out.columns:
        out[col] = out[col].map(lambda x: to_str(x).translate(FULLWIDTH).strip())
    return out


def drop_empty(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    ignore = {SOURCE_COLUMN, "source", "filename", "来源文件"}
    cols = [c for c in df.columns if str(c) not in ignore] or list(df.columns)
    mask = df[cols].apply(lambda row: any(to_str(v) != "" for v in row), axis=1)
    return df.loc[mask].copy(), int((~mask).sum())


def parse_one_date(raw: str, dayfirst: bool = False) -> str:
    text = raw.strip()
    if not text:
        return ""
    text = text.translate(FULLWIDTH)
    text = re.sub(r"[年月日./]", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    text = re.sub(r"\s+", " ", text)
    fmts = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m",
    ]
    if dayfirst:
        fmts.extend(["%d-%m-%Y", "%d-%m-%Y %H:%M:%S", "%m-%d-%Y"])
    else:
        fmts.extend(["%m-%d-%Y", "%m-%d-%Y %H:%M:%S"])
        parts = text.replace(" ", "-").split("-")
        if len(parts) >= 3 and parts[0].isdigit() and len(parts[0]) <= 2 and int(parts[0]) > 12:
            fmts.insert(4, "%d-%m-%Y")
    for fmt in fmts:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    if re.fullmatch(r"\d{8}", text):
        try:
            return datetime.strptime(text, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return raw
    parsed = pd.to_datetime(raw, errors="coerce", yearfirst=True, dayfirst=dayfirst)
    if pd.isna(parsed):
        parsed = pd.to_datetime(raw, errors="coerce", dayfirst=dayfirst)
    if pd.notna(parsed):
        return parsed.strftime("%Y-%m-%d")
    return raw


def normalize_dates(
    df: pd.DataFrame,
    date_cols: list[str] | None,
    dayfirst: bool = False,
) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    if date_cols:
        cols = [c for c in date_cols if c in out.columns]
    else:
        cols = [c for c in out.columns if DATE_CANDIDATES.search(str(c))]
    for col in cols:
        out[col] = out[col].map(lambda v, df=dayfirst: parse_one_date(to_str(v), dayfirst=df))
    return out, cols


def clean_frame(
    df: pd.DataFrame,
    date_cols: list[str] | None = None,
    dedupe_cols: list[str] | None = None,
    dayfirst: bool = False,
    seen_keys: set[tuple] | None = None,
) -> tuple[pd.DataFrame, dict, set[tuple] | None]:
    """Clean one DataFrame. If seen_keys is provided, dedupe across chunks."""
    report = {"input_rows": int(len(df)), "input_cols": int(df.shape[1])}
    df = strip_cells(df)
    df, empty_dropped = drop_empty(df)
    df, used_date_cols = normalize_dates(df, date_cols, dayfirst=dayfirst)

    subset = dedupe_cols if dedupe_cols else list(df.columns)
    missing = [c for c in subset if c not in df.columns]
    if missing:
        raise ValueError("Dedupe columns not found: " + ", ".join(missing))

    if seen_keys is None:
        before = len(df)
        df = df.drop_duplicates(subset=subset, keep="first")
        dupes = before - len(df)
    else:
        keys = [tuple(to_str(v) for v in row) for row in df[subset].itertuples(index=False, name=None)]
        keep: list[bool] = []
        dupes = 0
        for key in keys:
            if key in seen_keys:
                keep.append(False)
                dupes += 1
            else:
                seen_keys.add(key)
                keep.append(True)
        df = df.loc[keep].copy()

    report.update(
        {
            "empty_rows_dropped": empty_dropped,
            "date_cols": used_date_cols,
            "duplicates_removed": int(dupes),
            "output_rows": int(len(df)),
            "output_cols": int(df.shape[1]),
        }
    )
    return df.reset_index(drop=True), report, seen_keys
