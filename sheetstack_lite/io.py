"""Read and write CSV/Excel, including encoding sniffing and chunked CSV reads."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TABLE_SUFFIXES = {".csv", ".xlsx", ".xls"}

# latin-1/cp1252 must stay last: they can decode almost any byte string.
ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "utf-16",
    "gb18030",
    "gbk",
    "big5",
    "shift_jis",
    "cp932",
    "euc_jp",
    "cp1252",
    "latin-1",
)

EXCEL_MAX_ROWS = 1_048_576
# A practical cap so workbooks stay usable in Excel and WPS.
DEFAULT_SPLIT_ROWS = 300_000


def collect_inputs(items: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in items:
        path = Path(item)
        if path.is_dir():
            found = sorted(
                p for p in path.iterdir() if p.is_file() and p.suffix.lower() in TABLE_SUFFIXES
            )
            if not found:
                raise FileNotFoundError(f"No CSV or Excel files in {path}")
            paths.extend(found)
        elif path.is_file():
            paths.append(path)
        else:
            raise FileNotFoundError(f"File or folder not found: {path}")
    if not paths:
        raise FileNotFoundError("No input files to process")
    return paths


def _score_decoded(text: str) -> float:
    """Prefer decodes that look like real text, especially mixed CJK + kana."""
    if "\ufffd" in text:
        return -1000.0
    control = sum(1 for c in text if ord(c) < 32 and c not in "\t\n\r")
    pua = sum(1 for c in text if "\ue000" <= c <= "\uf8ff")
    kana = sum(1 for c in text if "\u3040" <= c <= "\u30ff")
    hangul = sum(1 for c in text if "\uac00" <= c <= "\ud7af")
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    return kana * 8 + hangul * 8 + cjk * 2 + latin * 0.5 - control * 50 - pua * 20


def sniff_encoding(path: Path, encoding: str | None = "auto") -> str:
    if encoding and encoding != "auto":
        return encoding
    raw = path.read_bytes()
    sample = raw[:65536]
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if sample.startswith(b"\xff\xfe") or sample.startswith(b"\xfe\xff"):
        return "utf-16"

    # Valid UTF-8 is authoritative: do not "fall through" to latin-1/GBK.
    for enc in ("utf-8-sig", "utf-8"):
        try:
            sample.decode(enc)
            pd.read_csv(path, encoding=enc, dtype=str, keep_default_na=False, nrows=5)
            return enc
        except Exception:
            pass

    last_err: Exception | None = None
    ranked: list[tuple[float, str]] = []
    for enc in ENCODINGS:
        if enc in {"utf-8-sig", "utf-8", "utf-16", "latin-1"}:
            continue
        try:
            text = sample.decode(enc)
            pd.read_csv(path, encoding=enc, dtype=str, keep_default_na=False, nrows=5)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
        ranked.append((_score_decoded(text), enc))
    if ranked:
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[0][1]

    # Last resort: latin-1 always decodes, but it is often the wrong choice.
    try:
        pd.read_csv(path, encoding="latin-1", dtype=str, keep_default_na=False, nrows=5)
        return "latin-1"
    except Exception as exc:  # noqa: BLE001
        last_err = exc
    raise RuntimeError(f"Could not decode {path.name}: {last_err}")


def read_table(path: Path, encoding: str | None = "auto") -> tuple[pd.DataFrame, str]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path, dtype=str, keep_default_na=False)
        df.columns = [str(c).strip() for c in df.columns]
        return df, "excel"
    used = sniff_encoding(path, encoding)
    df = pd.read_csv(path, encoding=used, dtype=str, keep_default_na=False)
    df.columns = [str(c).strip() for c in df.columns]
    return df, used


def iter_csv_chunks(
    path: Path,
    encoding: str,
    chunk_size: int,
) -> "pd.io.parsers.readers.TextFileReader":
    return pd.read_csv(
        path,
        encoding=encoding,
        dtype=str,
        keep_default_na=False,
        chunksize=chunk_size,
    )


def read_header_only(path: Path, encoding: str | None = "auto") -> tuple[list[str], str]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path, dtype=str, nrows=0)
        return [str(c).strip() for c in df.columns], "excel"
    used = sniff_encoding(path, encoding)
    df = pd.read_csv(path, encoding=used, dtype=str, nrows=0)
    return [str(c).strip() for c in df.columns], used


def write_table(df: pd.DataFrame, output: Path, *, header: bool = True, mode: str = "w") -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() in {".xlsx", ".xls"}:
        if mode != "w":
            raise ValueError("Chunked writes are supported for CSV outputs only")
        df.to_excel(output, index=False)
        return
    df.to_csv(
        output,
        index=False,
        encoding="utf-8-sig",
        mode=mode,
        header=header,
    )
