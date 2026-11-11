from __future__ import annotations

from pathlib import Path

import pandas as pd

from sheetstack_lite.headers import SOURCE_COLUMN, apply_header_aliases
from sheetstack_lite.io import read_table


def merge_tables(
    paths: list[Path],
    add_source: bool = True,
    encoding: str | None = "auto",
    normalize_headers: bool = False,
) -> tuple[pd.DataFrame, list[dict]]:
    frames: list[pd.DataFrame] = []
    logs: list[dict] = []
    for path in paths:
        df, used = read_table(path, encoding)
        if add_source:
            df.insert(0, SOURCE_COLUMN, path.name)
        if normalize_headers:
            df = apply_header_aliases(df)
        frames.append(df)
        logs.append({"file": path.name, "encoding": used, "rows": int(len(df)), "cols": int(df.shape[1])})
    merged = pd.concat(frames, axis=0, ignore_index=True, sort=False)
    if normalize_headers:
        merged = apply_header_aliases(merged)
    return merged, logs
