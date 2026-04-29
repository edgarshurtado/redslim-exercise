import datetime
import io
import shutil
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from market_data.models import Brand, Data, Market, Product, SubBrand


LEAF_LEVEL = "MANUFACTURER!SEGMENT!SUB SEGMENT!BRAND!SUB BRAND!PROMO/NON PROMO!SIZE!ITEM"


@pytest.fixture
def data_dir():
    path = Path(__file__).resolve().parents[3] / "docs" / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def write_parquet_folder(data_dir):
    """Write a folder of fixture parquet files under docs/data/<name>/.

    Pass `mkt`, `per`, `prod`, `data` DataFrames; pass `None` to omit a file
    (lets us test missing-required-file errors). `fct=False` skips the
    ignored fct file (default writes a tiny stub so the folder looks real).
    """
    written = []

    def _write(name, *, mkt=None, per=None, prod=None, data=None, fct=True):
        folder = data_dir / name
        folder.mkdir(parents=True, exist_ok=True)
        prefix = "fixture"
        if mkt is not None:
            mkt.to_parquet(folder / f"{prefix}_mkt.parquet")
        if per is not None:
            per.to_parquet(folder / f"{prefix}_per.parquet")
        if prod is not None:
            prod.to_parquet(folder / f"{prefix}_prod.parquet")
        if data is not None:
            data.to_parquet(folder / f"{prefix}_data.parquet")
        if fct:
            pd.DataFrame({"x": [1]}).to_parquet(folder / f"{prefix}_fct.parquet")
        written.append(folder)
        return name

    yield _write

    for folder in written:
        shutil.rmtree(folder, ignore_errors=True)


def mkt_df(rows):
    """rows: list of (tag, short, long)."""
    return pd.DataFrame(rows, columns=["TAG", "SHORT", "LONG"])


def per_df(rows):
    """rows: list of (tag, iso_date)."""
    return pd.DataFrame(
        [{"TAG": t, "DATETIME": datetime.date.fromisoformat(d)} for t, d in rows]
    )


def prod_df(rows, level=LEAF_LEVEL):
    """rows: list of (tag, sdesc, gl_brand, gl_sub_brand)."""
    return pd.DataFrame(
        [
            {"TAG": t, "SDESC": s, "LEVEL": level, "GL Brand": b, "GL Sub Brand": sb}
            for t, s, b, sb in rows
        ]
    )


def data_df(rows):
    """rows: list of dicts with MARKET_TAG, PRODUCT_TAG, PERIOD_TAG, VAL, WTD."""
    return pd.DataFrame(
        rows, columns=["MARKET_TAG", "PRODUCT_TAG", "PERIOD_TAG", "VAL", "WTD"]
    )
