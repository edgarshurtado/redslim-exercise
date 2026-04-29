# Load Parquet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Django management command `load_parquet` that imports a folder of five parquet files (one fact + four dimension files) into the existing five-model schema, optimized for the ~2.5M-row data file.

**Architecture:** Hybrid approach — load all small companion files into memory and bulk-insert dimensions, build TAG→PK dicts, then stream the data file in chunks (`pyarrow.ParquetFile.iter_batches`) and `bulk_create(ignore_conflicts=True)` `Data` rows. A single `transaction.atomic()` wraps the whole import. Idempotency is enforced by unique constraints on every dimension and on `Data(market, product, date)` (added by a new migration).

**Tech Stack:** Django 5, PostgreSQL, pandas, pyarrow, pytest-django.

**Spec:** [`docs/specs/008_load_parquet.md`](../../specs/008_load_parquet.md)

---

## File Structure

| File | Created/Modified | Responsibility |
|---|---|---|
| `backend/requirements.txt` | Modify | Add `pyarrow` dependency |
| `backend/market_data/models.py` | Modify | Add `UniqueConstraint` to each model's `Meta.constraints` |
| `backend/market_data/migrations/0005_unique_constraints.py` | Create | DB-level unique constraints |
| `backend/market_data/management/commands/load_parquet.py` | Create | The command (single file, internal helpers split into private methods) |
| `backend/market_data/tests/test_load_parquet.py` | Create | All 12 tests + fixtures + parquet builders |

The `load_parquet.py` command keeps file discovery, dimension loading, and data streaming as separate **private methods** on the `Command` class. Each method has one responsibility and is small enough to read at a glance. No separate module is needed because the loader's pieces are tightly coupled to a single use case.

---

## Conventions used by this plan

- All `pytest` invocations are run from the `backend/` directory: `cd backend && pytest path -v`. The project has `pytest.ini` at `backend/pytest.ini` configured with `DJANGO_SETTINGS_MODULE=redslim.settings`.
- Commit messages follow the existing pattern in `git log` (e.g. `feat:`, `test:`, `fix:`, `docs:`).
- The constant `LEAF_LEVEL = "MANUFACTURER!SEGMENT!SUB SEGMENT!BRAND!SUB BRAND!PROMO/NON PROMO!SIZE!ITEM"` appears in both the command and the tests.
- VAL scaling: parquet `VAL` is in millions of DKK; multiply by 1,000,000 to store raw DKK in `Data.value`.
- All code blocks below are the **exact final content** for the step they belong to.

---

## Task 1: Add `pyarrow` to requirements

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the dependency**

Append `pyarrow>=15.0` to `backend/requirements.txt` so it ends up:

```
django>=5.0,<6.0
djangorestframework>=3.15
django-cors-headers>=4.3
pandas>=2.2
psycopg2-binary>=2.9
python-dotenv>=1.0
pytest-django>=4.8
pyarrow>=15.0
```

- [ ] **Step 2: Install it in the dev venv**

Run: `backend/venv/bin/pip install -r backend/requirements.txt`
Expected: `pyarrow` installs (or "already satisfied").

- [ ] **Step 3: Verify it imports**

Run: `backend/venv/bin/python -c "import pyarrow.parquet; print(pyarrow.__version__)"`
Expected: a version string (no error).

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps: add pyarrow for parquet I/O"
```

---

## Task 2: Add unique constraints to models + migration

**Files:**
- Modify: `backend/market_data/models.py`
- Create: `backend/market_data/migrations/0005_unique_constraints.py`

- [ ] **Step 1: Update `models.py`**

Replace the entire file with:

```python
from django.db import models


class Brand(models.Model):
    description = models.CharField(max_length=255)

    class Meta:
        db_table = 'brand'
        constraints = [
            models.UniqueConstraint(
                fields=['description'],
                name='uniq_brand_description',
            ),
        ]


class SubBrand(models.Model):
    description = models.CharField(max_length=255)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, db_column='brand_fk')

    class Meta:
        db_table = 'subbrand'
        constraints = [
            models.UniqueConstraint(
                fields=['description', 'brand'],
                name='uniq_subbrand_description_brand',
            ),
        ]


class Product(models.Model):
    description = models.CharField(max_length=500)
    sub_brand = models.ForeignKey(SubBrand, on_delete=models.CASCADE, db_column='sub_brand_fk')

    class Meta:
        db_table = 'product'
        constraints = [
            models.UniqueConstraint(
                fields=['description', 'sub_brand'],
                name='uniq_product_description_subbrand',
            ),
        ]


class Market(models.Model):
    description = models.CharField(max_length=255)
    description_2 = models.CharField(max_length=255)

    class Meta:
        db_table = 'market'
        constraints = [
            models.UniqueConstraint(
                fields=['description', 'description_2'],
                name='uniq_market_descriptions',
            ),
        ]


class Data(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, db_column='market_fk')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_fk')
    value = models.DecimalField(max_digits=12, decimal_places=2)
    weighted_distribution = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    date = models.DateField()
    period_weeks = models.IntegerField()

    class Meta:
        db_table = 'sales_data'
        constraints = [
            models.UniqueConstraint(
                fields=['market', 'product', 'date'],
                name='uniq_data_market_product_date',
            ),
        ]
```

- [ ] **Step 2: Generate the migration**

Run: `cd backend && venv/bin/python manage.py makemigrations market_data`
Expected output mentions `0005_*.py` with `AddConstraint` operations for all five models. Rename the generated file to `0005_unique_constraints.py` if Django gave it a less descriptive name:

```bash
mv backend/market_data/migrations/0005_*.py backend/market_data/migrations/0005_unique_constraints.py
```

(If the move overwrites itself because the name already matches, that's fine.)

- [ ] **Step 3: Apply the migration**

Run: `cd backend && venv/bin/python manage.py migrate market_data`
Expected: `Applying market_data.0005_unique_constraints... OK`

- [ ] **Step 4: Verify existing tests still pass**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_csv.py -v`
Expected: all tests green. The unique constraints don't affect `get_or_create` semantics.

- [ ] **Step 5: Commit**

```bash
git add backend/market_data/models.py backend/market_data/migrations/0005_unique_constraints.py
git commit -m "feat: add unique constraints to market_data models"
```

---

## Task 3: Test infrastructure — fixtures and parquet builders

**Files:**
- Create: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Create the test file with shared helpers**

Create `backend/market_data/tests/test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Sanity-check the fixture by collecting tests**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py --collect-only -q`
Expected: `0 tests collected` (no tests yet, just helpers — no errors).

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: add fixtures and parquet builders for load_parquet tests"
```

---

## Task 4: Folder-not-found CommandError

**Files:**
- Create: `backend/market_data/management/commands/load_parquet.py`
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the failing test**

Append to `test_load_parquet.py`:

```python
@pytest.mark.django_db
def test_folder_not_found():
    with pytest.raises(CommandError, match="Folder not found"):
        call_command("load_parquet", "this_folder_does_not_exist_xyz")
```

- [ ] **Step 2: Run it and watch it fail with "Unknown command"**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_folder_not_found -v`
Expected: FAIL with `CommandError: Unknown command: 'load_parquet'`.

- [ ] **Step 3: Create the command skeleton**

Create `backend/market_data/management/commands/load_parquet.py`:

```python
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Load retail sales data from parquet files in docs/data/<foldername>/"

    def add_arguments(self, parser):
        parser.add_argument(
            "foldername",
            type=str,
            help="Folder name in docs/data/",
        )

    def handle(self, *args, **options):
        foldername = options["foldername"]
        folder = (
            Path(__file__).resolve().parents[4] / "docs" / "data" / foldername
        )
        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_folder_not_found -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/market_data/management/commands/load_parquet.py backend/market_data/tests/test_load_parquet.py
git commit -m "feat(load_parquet): skeleton command + folder-not-found error"
```

---

## Task 5: Missing-required-file errors

**Files:**
- Modify: `backend/market_data/management/commands/load_parquet.py`
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the failing test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_missing_required_file -v`
Expected: FAIL — the command currently exits cleanly without checking for files.

- [ ] **Step 3: Add file discovery to the command**

Replace `backend/market_data/management/commands/load_parquet.py` with:

```python
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


REQUIRED_SUFFIXES = {
    "data": "_data.parquet",
    "mkt": "_mkt.parquet",
    "per": "_per.parquet",
    "prod": "_prod.parquet",
}


class Command(BaseCommand):
    help = "Load retail sales data from parquet files in docs/data/<foldername>/"

    def add_arguments(self, parser):
        parser.add_argument(
            "foldername",
            type=str,
            help="Folder name in docs/data/",
        )

    def handle(self, *args, **options):
        foldername = options["foldername"]
        folder = (
            Path(__file__).resolve().parents[4] / "docs" / "data" / foldername
        )
        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")

        self._discover_files(folder)

    def _discover_files(self, folder):
        paths = {}
        for key, suffix in REQUIRED_SUFFIXES.items():
            matches = sorted(folder.glob(f"*{suffix}"))
            if not matches:
                raise CommandError(
                    f"Missing required file matching *{suffix} in {folder}"
                )
            if len(matches) > 1:
                raise CommandError(
                    f"Multiple files match *{suffix} in {folder}: {matches}"
                )
            paths[key] = matches[0]
        return paths
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_missing_required_file -v`
Expected: 4 PASS (one per parametrized case).

- [ ] **Step 5: Commit**

```bash
git add backend/market_data/management/commands/load_parquet.py backend/market_data/tests/test_load_parquet.py
git commit -m "feat(load_parquet): error on missing required dimension/data file"
```

---

## Task 6: Happy path — full loader implementation

This task is the bulk of the implementation. The happy-path test drives building all three phases (dimensions, periods, data). Subsequent tasks add edge-case tests that mostly already pass and only require small tweaks.

**Files:**
- Modify: `backend/market_data/management/commands/load_parquet.py`
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the failing happy-path test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_happy_path -v`
Expected: FAIL — `Brand.objects.count() == 0` (the loader currently only validates files, doesn't load anything).

- [ ] **Step 3: Implement the full loader**

Replace `backend/market_data/management/commands/load_parquet.py` with:

```python
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from market_data.models import Brand, Data, Market, Product, SubBrand


REQUIRED_SUFFIXES = {
    "data": "_data.parquet",
    "mkt": "_mkt.parquet",
    "per": "_per.parquet",
    "prod": "_prod.parquet",
}

LEAF_LEVEL = "MANUFACTURER!SEGMENT!SUB SEGMENT!BRAND!SUB BRAND!PROMO/NON PROMO!SIZE!ITEM"
DATA_BATCH_SIZE = 50_000
BULK_CREATE_BATCH_SIZE = 10_000
VAL_SCALE = 1_000_000
PERIOD_WEEKS = 4
TWO_DP = Decimal("0.01")


class Command(BaseCommand):
    help = "Load retail sales data from parquet files in docs/data/<foldername>/"

    def add_arguments(self, parser):
        parser.add_argument(
            "foldername",
            type=str,
            help="Folder name in docs/data/",
        )

    def handle(self, *args, **options):
        foldername = options["foldername"]
        folder = (
            Path(__file__).resolve().parents[4] / "docs" / "data" / foldername
        )
        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")

        paths = self._discover_files(folder)

        with transaction.atomic():
            mkt_df = pd.read_parquet(paths["mkt"])
            per_df = pd.read_parquet(paths["per"])
            prod_df = pd.read_parquet(paths["prod"])

            prod_df = prod_df[prod_df["LEVEL"] == LEAF_LEVEL]
            if prod_df.empty:
                raise CommandError(
                    f"No leaf-level products in {paths['prod'].name}"
                )

            brand_id_by_desc = self._load_brands(prod_df)
            subbrand_id_by_pair = self._load_subbrands(prod_df, brand_id_by_desc)
            product_id_by_tag = self._load_products(
                prod_df, brand_id_by_desc, subbrand_id_by_pair
            )
            market_id_by_tag = self._load_markets(mkt_df)
            date_by_tag = dict(zip(per_df["TAG"], per_df["DATETIME"]))

            count_before = Data.objects.count()
            self._load_data(
                paths["data"],
                market_id_by_tag,
                product_id_by_tag,
                date_by_tag,
            )
            loaded = Data.objects.count() - count_before

        self.stdout.write(f"Loaded {loaded} rows from {foldername}.")

    def _discover_files(self, folder):
        paths = {}
        for key, suffix in REQUIRED_SUFFIXES.items():
            matches = sorted(folder.glob(f"*{suffix}"))
            if not matches:
                raise CommandError(
                    f"Missing required file matching *{suffix} in {folder}"
                )
            if len(matches) > 1:
                raise CommandError(
                    f"Multiple files match *{suffix} in {folder}: {matches}"
                )
            paths[key] = matches[0]
        return paths

    def _load_brands(self, prod_df):
        descs = set(prod_df["GL Brand"].dropna())
        Brand.objects.bulk_create(
            [Brand(description=d) for d in descs],
            ignore_conflicts=True,
        )
        return {
            b.description: b.pk
            for b in Brand.objects.filter(description__in=descs)
        }

    def _load_subbrands(self, prod_df, brand_id_by_desc):
        pairs = set(zip(prod_df["GL Sub Brand"], prod_df["GL Brand"]))
        SubBrand.objects.bulk_create(
            [
                SubBrand(description=sub, brand_id=brand_id_by_desc[brand])
                for sub, brand in pairs
            ],
            ignore_conflicts=True,
        )
        brand_ids = list(brand_id_by_desc.values())
        return {
            (sb.description, sb.brand_id): sb.pk
            for sb in SubBrand.objects.filter(brand_id__in=brand_ids)
        }

    def _load_products(self, prod_df, brand_id_by_desc, subbrand_id_by_pair):
        instances = [
            Product(
                description=row.SDESC,
                sub_brand_id=subbrand_id_by_pair[
                    (getattr(row, "_3"), brand_id_by_desc[getattr(row, "_2")])
                ],
            )
            for row in prod_df.itertuples(index=False)
        ]
        # itertuples() renames columns containing spaces; use positional names
        # via a fresh DataFrame to avoid that.
        Product.objects.bulk_create(instances, ignore_conflicts=True)

        sub_brand_ids = list(subbrand_id_by_pair.values())
        natural = {
            (p.description, p.sub_brand_id): p.pk
            for p in Product.objects.filter(sub_brand_id__in=sub_brand_ids)
        }
        return {
            tag: natural[
                (
                    sdesc,
                    subbrand_id_by_pair[(sub, brand_id_by_desc[brand])],
                )
            ]
            for tag, sdesc, sub, brand in zip(
                prod_df["TAG"],
                prod_df["SDESC"],
                prod_df["GL Sub Brand"],
                prod_df["GL Brand"],
            )
        }

    def _load_markets(self, mkt_df):
        instances = [
            Market(description=short, description_2=long_)
            for short, long_ in zip(mkt_df["SHORT"], mkt_df["LONG"])
        ]
        Market.objects.bulk_create(instances, ignore_conflicts=True)
        descs = set(mkt_df["SHORT"])
        natural = {
            (m.description, m.description_2): m.pk
            for m in Market.objects.filter(description__in=descs)
        }
        return {
            tag: natural[(short, long_)]
            for tag, short, long_ in zip(
                mkt_df["TAG"], mkt_df["SHORT"], mkt_df["LONG"]
            )
        }

    def _load_data(
        self,
        data_path,
        market_id_by_tag,
        product_id_by_tag,
        date_by_tag,
    ):
        pf = pq.ParquetFile(str(data_path))
        for batch in pf.iter_batches(batch_size=DATA_BATCH_SIZE):
            df = batch.to_pandas()
            df = df.dropna(subset=["VAL"])
            df = df[df["MARKET_TAG"].isin(market_id_by_tag)]
            df = df[df["PRODUCT_TAG"].isin(product_id_by_tag)]
            df = df[df["PERIOD_TAG"].isin(date_by_tag)]
            rows = [
                Data(
                    market_id=market_id_by_tag[mkt_tag],
                    product_id=product_id_by_tag[prod_tag],
                    date=date_by_tag[per_tag],
                    value=(Decimal(str(val)) * VAL_SCALE).quantize(TWO_DP),
                    weighted_distribution=(
                        None if pd.isna(wtd)
                        else Decimal(str(wtd)).quantize(TWO_DP)
                    ),
                    period_weeks=PERIOD_WEEKS,
                )
                for mkt_tag, prod_tag, per_tag, val, wtd in zip(
                    df["MARKET_TAG"],
                    df["PRODUCT_TAG"],
                    df["PERIOD_TAG"],
                    df["VAL"],
                    df["WTD"],
                )
            ]
            Data.objects.bulk_create(
                rows,
                ignore_conflicts=True,
                batch_size=BULK_CREATE_BATCH_SIZE,
            )
```

**Note about `_load_products`:** `df.itertuples()` mangles column names with spaces (e.g. `GL Sub Brand` → `_3`), which is brittle. The version above uses `zip(df["..."], ...)` everywhere to keep the code readable. The `instances = [...]` list-comp at the top is rewritten the same way — replace it with:

```python
        instances = [
            Product(
                description=sdesc,
                sub_brand_id=subbrand_id_by_pair[
                    (sub, brand_id_by_desc[brand])
                ],
            )
            for sdesc, sub, brand in zip(
                prod_df["SDESC"],
                prod_df["GL Sub Brand"],
                prod_df["GL Brand"],
            )
        ]
```

(The full `_load_products` method ends up using `zip` for both the create list and the return dict — no `itertuples`.)

- [ ] **Step 4: Run the happy-path test**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_happy_path -v`
Expected: PASS.

- [ ] **Step 5: Run the full file**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py -v`
Expected: 6 PASS (1 happy + 4 parametrized missing-file + 1 folder-not-found).

- [ ] **Step 6: Commit**

```bash
git add backend/market_data/management/commands/load_parquet.py backend/market_data/tests/test_load_parquet.py
git commit -m "feat(load_parquet): implement happy-path dimension + data load"
```

---

## Task 7: Idempotency

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_idempotency -v`
Expected: PASS — `bulk_create(ignore_conflicts=True)` + the new unique constraints handle this for free.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: idempotency on re-run for load_parquet"
```

---

## Task 8: Brand de-dup across products

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_brand_dedup -v`
Expected: PASS — the in-memory `set(prod_df["GL Brand"])` already de-duplicates.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: brand de-dup across multiple products"
```

---

## Task 9: Non-leaf product filter

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_non_leaf_prod_filter -v`
Expected: PASS — the `prod_df = prod_df[prod_df["LEVEL"] == LEAF_LEVEL]` filter handles this; the `df = df[df["PRODUCT_TAG"].isin(product_id_by_tag)]` line in `_load_data` drops the dangling data row.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: non-leaf prod rows skipped, data rows pointing at them dropped"
```

---

## Task 10: NaN VAL skipped

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_nan_val_skipped -v`
Expected: PASS — `df.dropna(subset=["VAL"])` already handles this.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: NaN VAL rows skipped"
```

---

## Task 11: NaN WTD stored as NULL

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_nan_wtd_stored_as_null -v`
Expected: PASS — the `pd.isna(wtd)` check in `_load_data` already handles this.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: NaN WTD stored as NULL"
```

---

## Task 12: VAL scaling precision

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_val_scaling -v`
Expected: PASS — `(Decimal(str(0.0011)) * 1_000_000).quantize(Decimal("0.01"))` → `Decimal("1100.00")`.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: VAL scaling preserves precision for small values"
```

---

## Task 13: Dangling TAG silent-skip

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
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
```

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_dangling_tag_silent_skip -v`
Expected: PASS — the three `df = df[df["..."].isin(...)]` filters in `_load_data` drop the dangling rows.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: data rows with unknown TAG references silently skipped"
```

---

## Task 14: Unique-constraint idempotency for duplicate input rows

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
@pytest.mark.django_db
def test_duplicate_input_rows_collapse(write_parquet_folder):
    folder = write_parquet_folder(
        "test_dup_input",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=prod_df([("PR1", "PROD", "B1", "S1")]),
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": 1.0, "WTD": 50.0},
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": 2.0, "WTD": 60.0},
        ]),
    )
    out = io.StringIO()
    call_command("load_parquet", folder, stdout=out)

    assert Data.objects.count() == 1
    assert "Loaded 1 rows" in out.getvalue()
```

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_duplicate_input_rows_collapse -v`
Expected: PASS — the `Data` unique constraint on `(market, product, date)` plus `bulk_create(ignore_conflicts=True)` keep the first row and drop the second.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: duplicate input rows collapsed by unique constraint"
```

---

## Task 15: Rollback on mid-import error

**Files:**
- Modify: `backend/market_data/tests/test_load_parquet.py`

- [ ] **Step 1: Write the test**

Append to `test_load_parquet.py`:

```python
@pytest.mark.django_db(transaction=True)
def test_rollback_on_data_bulk_create_error(write_parquet_folder, monkeypatch):
    folder = write_parquet_folder(
        "test_rollback",
        mkt=mkt_df([("M1", "S", "L")]),
        per=per_df([("P1", "2020-01-05")]),
        prod=prod_df([("PR1", "PROD", "B1", "S1")]),
        data=data_df([
            {"MARKET_TAG": "M1", "PRODUCT_TAG": "PR1",
             "PERIOD_TAG": "P1", "VAL": 1.0, "WTD": 50.0},
        ]),
    )

    from django.db.models import Manager
    original = Manager.bulk_create

    def explode_for_data(self, objs, *args, **kwargs):
        if self.model is Data:
            raise RuntimeError("simulated mid-import failure")
        return original(self, objs, *args, **kwargs)

    monkeypatch.setattr(Manager, "bulk_create", explode_for_data)

    with pytest.raises(RuntimeError, match="simulated mid-import failure"):
        call_command("load_parquet", folder)

    assert Brand.objects.count() == 0
    assert SubBrand.objects.count() == 0
    assert Product.objects.count() == 0
    assert Market.objects.count() == 0
    assert Data.objects.count() == 0
```

**Why `@pytest.mark.django_db(transaction=True)`:** the default `django_db` mark wraps each test in a transaction that is rolled back at the end. We need the loader's *own* `transaction.atomic()` to be the rollback boundary, so the test must commit between savepoints — `transaction=True` switches to truncating cleanup instead. (See `test_load_csv.test_invalid_time_rolls_back` — it works with the default mark because the rollback happens before the outer test transaction commits; we use `transaction=True` here to be explicit and avoid coupling to that detail.)

- [ ] **Step 2: Run it**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py::test_rollback_on_data_bulk_create_error -v`
Expected: PASS — the loader's outer `transaction.atomic()` rolls back the brand/subbrand/product/market inserts when `Data.objects.bulk_create` raises.

- [ ] **Step 3: Run the full suite**

Run: `cd backend && venv/bin/pytest market_data/tests/test_load_parquet.py -v`
Expected: 14+ tests PASS (1 happy + 4 missing-file + 1 folder-not-found + idempotency + brand-dedup + non-leaf + nan-val + nan-wtd + val-scaling + dangling + duplicate + rollback).

- [ ] **Step 4: Run the full project suite**

Run: `cd backend && venv/bin/pytest -v`
Expected: all green — no regressions in `test_load_csv` or other tests.

- [ ] **Step 5: Commit**

```bash
git add backend/market_data/tests/test_load_parquet.py
git commit -m "test: rollback all dimension inserts on Data bulk_create failure"
```

---

## Task 16: End-to-end smoke check on real data

**Files:**
- (no code changes)

- [ ] **Step 1: Move the sample dataset under `docs/data/`**

```bash
mkdir -p docs/data/unistar_dk
mv unistar_dk/*.parquet docs/data/unistar_dk/
rmdir unistar_dk
```

(If `mv` fails because `docs/data/unistar_dk/` already exists, the parquet files are already in place — skip.)

- [ ] **Step 2: Run the loader against the real folder**

```bash
cd backend && venv/bin/python manage.py load_parquet unistar_dk
```

Expected output: `Loaded N rows from unistar_dk.` where N is on the order of 2.5M minus dropped rows (NaN VAL + non-leaf product references). Wall time: a few minutes on a typical dev box.

- [ ] **Step 3: Spot-check the DB**

```bash
cd backend && venv/bin/python manage.py shell -c "
from market_data.models import Brand, SubBrand, Product, Market, Data
print('Brand:', Brand.objects.count())
print('SubBrand:', SubBrand.objects.count())
print('Product:', Product.objects.count())
print('Market:', Market.objects.count())
print('Data:', Data.objects.count())
"
```

Expected: Brand ≪ 7117, SubBrand < 7117, Product close to the leaf-level subset of 7117, Market = 29, Data on the order of 2M+.

- [ ] **Step 4: Run again to confirm idempotency**

```bash
cd backend && venv/bin/python manage.py load_parquet unistar_dk
```

Expected: `Loaded 0 rows from unistar_dk.`

- [ ] **Step 5: Commit the data move**

```bash
git add docs/data/unistar_dk/ 2>/dev/null || true
git status
# If the parquet files are not gitignored and you DO want them committed, run:
#   git add docs/data/unistar_dk/
#   git commit -m "data: move sample parquet dataset under docs/data/"
# If they're large and gitignored, just commit any .gitkeep / readme:
#   git commit --allow-empty -m "chore: smoke-test load_parquet on sample dataset"
```

(The decision whether to commit the parquet files belongs to the user; if `.gitignore` already excludes `docs/data/*.parquet`, leave them out.)

---

## Self-Review

**Spec coverage (cross-checked against `docs/specs/008_load_parquet.md`):**

| Spec section | Covered by |
|---|---|
| Input layout (5 files, suffix matching) | Task 5 (`_discover_files`), Task 4 (folder check) |
| Command interface, output line | Task 4, Task 6 |
| `pyarrow` dependency | Task 1 |
| Migration with 5 unique constraints | Task 2 |
| Phase 1 — Brand/SubBrand/Product/Market loading | Task 6 (`_load_brands`, `_load_subbrands`, `_load_products`, `_load_markets`) |
| Phase 1 — leaf-level product filter | Task 6 (handle method); Task 9 (test) |
| Phase 1 — periods dict | Task 6 (`date_by_tag = dict(zip(...))`) |
| Phase 2 — streamed bulk insert | Task 6 (`_load_data`) |
| Phase 3 — output line with count diff | Task 6 |
| Field derivations (VAL × 1M, WTD nullable, period_weeks=4) | Task 6; Task 12 (scaling); Task 11 (WTD); implicit in happy-path |
| Error: folder not found | Task 4 |
| Error: missing/duplicate required file | Task 5 |
| Error: empty leaf prod | Task 6 (handle raises CommandError) — **no dedicated test, but covered by `_prod`-empty CommandError pathway** |
| Silent skip on NaN VAL / dangling TAG | Tasks 10, 13 |
| Rollback on any other exception | Task 15 |
| Acceptance criteria 1–11 | Tasks 6–15 |
| Test #1 happy / #2 idem / #3 brand-dedup / #4 non-leaf / #5 nan-val / #6 nan-wtd / #7 val-scaling / #8 dangling / #9 folder-404 / #10 missing-file / #11 unique constraint / #12 rollback | Tasks 6 / 7 / 8 / 9 / 10 / 11 / 12 / 13 / 4 / 5 / 14 / 15 |

**Gap noted:** the spec lists "empty `_prod` after the LEAF_LEVEL filter → `CommandError`" in error handling, and the `handle` method raises it, but no dedicated test exercises that branch. Adding a one-line test is cheap — see addendum below.

**Addendum to Task 9 (drop-in extra test):** also append:

```python
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
```

Run the same way; expected PASS. Commit alongside Task 9.

**Placeholder scan:** searched the plan for `TBD`, `TODO`, `add appropriate`, `etc.`, `similar to`, `fill in` — none present.

**Type/name consistency:** `LEAF_LEVEL`, `REQUIRED_SUFFIXES`, `DATA_BATCH_SIZE`, `BULK_CREATE_BATCH_SIZE`, `VAL_SCALE`, `PERIOD_WEEKS`, `TWO_DP`, `_discover_files`, `_load_brands`, `_load_subbrands`, `_load_products`, `_load_markets`, `_load_data` are used consistently. Test helper names (`mkt_df`, `per_df`, `prod_df`, `data_df`, `write_parquet_folder`) are stable across all tests.
