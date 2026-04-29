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


@pytest.mark.django_db
def test_folder_not_found():
    with pytest.raises(CommandError, match="Folder not found"):
        call_command("load_parquet", "this_folder_does_not_exist_xyz")


@pytest.mark.django_db
@pytest.mark.parametrize("missing", ["data", "mkt", "per", "prod"])
def test_missing_required_file(write_parquet_folder, missing):
    kwargs = {
        "mkt": mkt_df([("M1", "S", "L")]),
        "per": per_df([("P1", "2020-01-01")]),
        "prod": prod_df([("PR1", "X", "B", "SB")]),
        "data": data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": 1.0, "WTD": 50.0},
        ]),
    }
    kwargs[missing] = None
    folder = write_parquet_folder("test_missing", **kwargs)

    with pytest.raises(CommandError, match=f"_{missing}.parquet"):
        call_command("load_parquet", folder)

    assert Brand.objects.count() == 0
    assert Data.objects.count() == 0


@pytest.mark.django_db
def test_happy_path(write_parquet_folder):
    folder = write_parquet_folder(
        "test_happy",
        mkt=mkt_df([
            ("M1", "DK SOUTH", "DK SOUTHWEST"),
            ("M2", "DK NORTH", "DK NORTHEAST"),
            ("M3", "DK EAST",  "DK EAST"),
        ]),
        per=per_df([
            ("P1", "2020-01-05"),
            ("P2", "2020-02-02"),
            ("P3", "2020-03-01"),
        ]),
        prod=prod_df([
            ("PR1", "PRODUCT ONE",   "BRAND A", "SUB A"),
            ("PR2", "PRODUCT TWO",   "BRAND A", "SUB B"),
            ("PR3", "PRODUCT THREE", "BRAND B", "SUB C"),
        ]),
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1", "PERIOD_TAG": "P1", "VAL": 0.0011, "WTD": 50.0},
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR2", "PERIOD_TAG": "P1", "VAL": 0.5,    "WTD": 60.0},
            {"MARKET_TAG": "M2", "PRODUCT_TAG": "PR3", "PERIOD_TAG": "P2", "VAL": 1.0,    "WTD": 70.0},
            {"MARKET_TAG": "M3", "PRODUCT_TAG": "PR1", "PERIOD_TAG": "P3", "VAL": 2.5,    "WTD": 80.0},
            {"MARKET_TAG": "M3", "PRODUCT_TAG": "PR2", "PERIOD_TAG": "P2", "VAL": 0.001,  "WTD": 90.0},
        ]),
    )
    out = io.StringIO()
    call_command("load_parquet", folder, stdout=out)

    assert Brand.objects.count() == 2
    assert SubBrand.objects.count() == 3
    assert Product.objects.count() == 3
    assert Market.objects.count() == 3
    assert Data.objects.count() == 5

    row = Data.objects.get(
        market__description="DK SOUTH",
        product__description="PRODUCT ONE",
        date=datetime.date(2020, 1, 5),
    )
    assert row.value == Decimal("1100.00")        # 0.0011 * 1_000_000
    assert row.weighted_distribution == Decimal("50.00")
    assert row.period_weeks == 4
    assert row.market.description_2 == "DK SOUTHWEST"
    assert row.product.sub_brand.description == "SUB A"
    assert row.product.sub_brand.brand.description == "BRAND A"

    assert "Loaded 5 rows from test_happy." in out.getvalue()


@pytest.mark.django_db
def test_idempotency(write_parquet_folder):
    folder = write_parquet_folder(
        "test_idem",
        mkt=mkt_df([("M1", "DK SOUTH", "DK SOUTHWEST")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=prod_df([
            ("PR1", "PROD ONE", "BRAND A", "SUB A"),
            ("PR2", "PROD TWO", "BRAND A", "SUB B"),
        ]),
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1", "PERIOD_TAG": "P1", "VAL": 1.0, "WTD": 50.0},
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR2", "PERIOD_TAG": "P1", "VAL": 2.0, "WTD": 60.0},
        ]),
    )

    out = io.StringIO()
    call_command("load_parquet", folder)
    call_command("load_parquet", folder, stdout=out)

    assert "Loaded 0 rows from test_idem." in out.getvalue()
    assert Brand.objects.count() == 1
    assert SubBrand.objects.count() == 2
    assert Product.objects.count() == 2
    assert Market.objects.count() == 1
    assert Data.objects.count() == 2


@pytest.mark.django_db
def test_brand_dedup(write_parquet_folder):
    folder = write_parquet_folder(
        "test_brand_dedup",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=prod_df([
            ("PR1", "PROD ONE", "SHARED BRAND", "SUB A"),
            ("PR2", "PROD TWO", "SHARED BRAND", "SUB B"),
        ]),
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1", "PERIOD_TAG": "P1", "VAL": 1.0, "WTD": 50.0},
        ]),
    )
    call_command("load_parquet", folder)

    assert Brand.objects.filter(description="SHARED BRAND").count() == 1
    assert SubBrand.objects.count() == 2
    assert Product.objects.count() == 2


@pytest.mark.django_db
def test_non_leaf_prod_filter(write_parquet_folder):
    leaf = LEAF_LEVEL
    aggregate = "MANUFACTURER!SEGMENT"

    prod = pd.DataFrame([
        {"TAG": "PR1", "SDESC": "LEAF",      "LEVEL": leaf,
         "GL Brand": "B1", "GL Sub Brand": "S1"},
        {"TAG": "PR2", "SDESC": "AGGREGATE", "LEVEL": aggregate,
         "GL Brand": "ALL OTHER", "GL Sub Brand": "ALL OTHER"},
    ])

    folder = write_parquet_folder(
        "test_non_leaf",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=prod,
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": 1.0, "WTD": 50.0},
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR2",
             "PERIOD_TAG": "P1", "VAL": 9.0, "WTD": 99.0},
        ]),
    )
    call_command("load_parquet", folder)

    assert Product.objects.count() == 1
    assert Product.objects.filter(description="LEAF").exists()
    assert not Product.objects.filter(description="AGGREGATE").exists()
    assert Data.objects.count() == 1
    assert Data.objects.first().product.description == "LEAF"


@pytest.mark.django_db
def test_empty_after_leaf_filter_raises(write_parquet_folder):
    only_aggregates = pd.DataFrame([
        {"TAG": "PR1", "SDESC": "X", "LEVEL": "MANUFACTURER",
         "GL Brand": "B", "GL Sub Brand": "S"},
    ])
    folder = write_parquet_folder(
        "test_empty_leaf",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=only_aggregates,
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": 1.0, "WTD": 50.0},
        ]),
    )
    with pytest.raises(CommandError, match="No leaf-level products"):
        call_command("load_parquet", folder)
    assert Brand.objects.count() == 0


@pytest.mark.django_db
def test_nan_val_skipped(write_parquet_folder):
    import numpy as np

    folder = write_parquet_folder(
        "test_nan_val",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05"), ("P2", "2020-02-02")]),
        prod=prod_df([("PR1", "PROD", "B1", "S1")]),
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": np.nan, "WTD": 50.0},
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P2", "VAL": 1.0,    "WTD": 60.0},
        ]),
    )

    out = io.StringIO()
    call_command("load_parquet", folder, stdout=out)

    assert Data.objects.count() == 1
    assert Data.objects.first().date == datetime.date(2020, 2, 2)
    assert "Loaded 1 rows" in out.getvalue()


@pytest.mark.django_db
def test_nan_wtd_stored_as_null(write_parquet_folder):
    import numpy as np

    folder = write_parquet_folder(
        "test_nan_wtd",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=prod_df([("PR1", "PROD", "B1", "S1")]),
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": 1.0, "WTD": np.nan},
        ]),
    )
    call_command("load_parquet", folder)

    row = Data.objects.get()
    assert row.weighted_distribution is None
    assert row.value == Decimal("1000000.00")


@pytest.mark.django_db
def test_val_scaling(write_parquet_folder):
    folder = write_parquet_folder(
        "test_val_scale",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=prod_df([("PR1", "PROD", "B1", "S1")]),
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": 0.0011, "WTD": 50.0},
        ]),
    )
    call_command("load_parquet", folder)

    row = Data.objects.get()
    assert row.value == Decimal("1100.00")


@pytest.mark.django_db
def test_dangling_tag_silent_skip(write_parquet_folder):
    folder = write_parquet_folder(
        "test_dangling",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=prod_df([("PR1", "PROD", "B1", "S1")]),
        data=data_df([
            {"MARKET_TAG": "M1",       "PRODUCT_TAG": "PR1", "PERIOD_TAG": "P1",       "VAL": 1.0, "WTD": 50.0},
            {"MARKET_TAG": "UNKNOWN",  "PRODUCT_TAG": "PR1", "PERIOD_TAG": "P1",       "VAL": 1.0, "WTD": 50.0},
            {"MARKET_TAG": "M1",       "PRODUCT_TAG": "X",   "PERIOD_TAG": "P1",       "VAL": 1.0, "WTD": 50.0},
            {"MARKET_TAG": "M1",       "PRODUCT_TAG": "PR1", "PERIOD_TAG": "UNKNOWN",  "VAL": 1.0, "WTD": 50.0},
        ]),
    )
    out = io.StringIO()
    call_command("load_parquet", folder, stdout=out)

    assert Data.objects.count() == 1
    assert "Loaded 1 rows" in out.getvalue()
