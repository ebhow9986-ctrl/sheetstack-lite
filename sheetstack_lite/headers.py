"""Normalize common export header names into a shared set of English columns."""
from __future__ import annotations

import pandas as pd

SOURCE_COLUMN = "source_file"

# Map frequent aliases onto a small set of canonical names.
# Values are English so merged files stay consistent for international users.
HEADER_ALIASES: dict[str, str] = {
    # order id
    "order id": "order_id",
    "order_id": "order_id",
    "orderid": "order_id",
    "order no": "order_id",
    "order_no": "order_id",
    "order number": "order_id",
    "订单号": "order_id",
    "订单编号": "order_id",
    "单号": "order_id",
    "伝票番号": "order_id",
    "受注番号": "order_id",
    # dates
    "date": "order_date",
    "order date": "order_date",
    "order_date": "order_date",
    "created": "order_date",
    "created at": "order_date",
    "timestamp": "order_date",
    "datetime": "order_date",
    "日期": "order_date",
    "下单日期": "order_date",
    "下单时间": "order_date",
    "成交时间": "order_date",
    "日付": "order_date",
    "受注日": "order_date",
    # product / item
    "product": "product",
    "product name": "product",
    "item": "product",
    "item name": "product",
    "sku name": "product",
    "商品": "product",
    "商品名称": "product",
    "品名": "product",
    "产品名称": "product",
    "商品名": "product",
    # qty
    "qty": "qty",
    "quantity": "qty",
    "units": "qty",
    "数量": "qty",
    "件数": "qty",
    # amount
    "amount": "amount",
    "sales": "amount",
    "revenue": "amount",
    "total": "amount",
    "price": "amount",
    "金额": "amount",
    "销售额": "amount",
    "收入": "amount",
    "売上": "amount",
    # stock
    "stock": "stock",
    "inventory": "stock",
    "qty on hand": "stock",
    "remaining": "stock",
    "库存": "stock",
    "库存数": "stock",
    "库存量": "stock",
    "余量": "stock",
    "在庫": "stock",
    # source
    "source": SOURCE_COLUMN,
    "source_file": SOURCE_COLUMN,
    "filename": SOURCE_COLUMN,
    "来源文件": SOURCE_COLUMN,
}


def canonical_name(name: object) -> str:
    text = str(name).strip()
    key = " ".join(text.lower().replace("_", " ").split())
    return HEADER_ALIASES.get(key, HEADER_ALIASES.get(text, text))


def coalesce_same_name_columns(df: pd.DataFrame) -> pd.DataFrame:
    """If several columns share a name, keep one using the first non-empty value."""
    if not df.columns.duplicated().any():
        return df
    out = pd.DataFrame(index=df.index)
    seen: list[str] = []
    for name in df.columns:
        if name in seen:
            continue
        seen.append(str(name))
        block = df.loc[:, df.columns == name]
        if block.shape[1] == 1:
            out[name] = block.iloc[:, 0]
            continue
        merged = block.iloc[:, 0].map(_cell)
        for i in range(1, block.shape[1]):
            extra = block.iloc[:, i].map(_cell)
            merged = merged.where(merged != "", extra)
        out[name] = merged
    return out.reset_index(drop=True)


def _cell(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def apply_header_aliases(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(columns=lambda c: canonical_name(c))
    return coalesce_same_name_columns(renamed)
