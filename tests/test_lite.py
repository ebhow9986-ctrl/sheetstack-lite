#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tests" / "_tmp"
PY = sys.executable


def run(args: list[str]) -> None:
    proc = subprocess.run([PY, str(ROOT / "sheetstack_lite.py"), *args], cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + proc.stderr)


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    merged = TMP / "merged.csv"
    run(["merge", str(ROOT / "samples"), "-o", str(merged), "--normalize-headers"])
    df = pd.read_csv(merged, dtype=str)
    assert {"store_us.csv", "store_uk.csv", "store_jp.csv", "store_cn.csv"} <= set(df["source_file"])
    assert "order_id" in df.columns
    cleaned = TMP / "customers.csv"
    run(
        [
            "clean",
            str(ROOT / "samples" / "customers_messy.csv"),
            "-o",
            str(cleaned),
            "--dedupe-cols",
            "customer_id",
            "--date-cols",
            "signup_date",
        ]
    )
    customers = pd.read_csv(cleaned, dtype=str)
    assert list(customers["customer_id"]) == ["U001", "U002", "U003", "U004", "U005"]
    assert list(customers["signup_date"]) == [
        "2026-02-01",
        "2026-02-03",
        "2026-02-08",
        "2026-02-11",
        "2026-02-15",
    ]
    print("Lite tests passed")
    return 0


def test_lite() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
