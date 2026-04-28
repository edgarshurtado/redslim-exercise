# weighted_distribution: nullable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow `Data.weighted_distribution` to be NULL so that CSV rows with an empty WTD column are accepted instead of rejected.

**Architecture:** Two-step TDD change — model + migration first, then loader. The model field gains `null=True, blank=True`; a new migration alters the column; the loader replaces its `try/except` WTD block with a conditional that stores `None` when the cell is empty and still raises `ValueError` when the cell is non-empty but unparseable.

**Tech Stack:** Django ORM (`DecimalField`), Django migrations, pytest-django, Python `decimal.Decimal`

---

## Files

- Modify: `backend/market_data/models.py:39`
- Create: `backend/market_data/migrations/0004_alter_data_weighted_distribution_nullable.py` (via `makemigrations`)
- Modify: `backend/market_data/tests/test_models.py`
- Modify: `backend/market_data/management/commands/load_csv.py`
- Modify: `backend/market_data/tests/test_load_csv.py`

---

### Task 1: Model field + migration

**Files:**
- Modify: `backend/market_data/models.py:39`
- Create: `backend/market_data/migrations/0004_alter_data_weighted_distribution_nullable.py`
- Modify: `backend/market_data/tests/test_models.py`

- [ ] **Step 1: Add a failing test for null weighted_distribution**

Append this test to `backend/market_data/tests/test_models.py` (after the existing imports — `date` and `Decimal` are already imported):

```python
@pytest.mark.django_db
def test_data_weighted_distribution_can_be_null():
    brand = Brand.objects.create(description="BRAND X")
    subbrand = SubBrand.objects.create(description="SUBBRAND X", brand=brand)
    product = Product.objects.create(description="PRODUCT X", sub_brand=subbrand)
    market = Market.objects.create(description="MARKET X", description_2="RETAILER X")
    data = Data.objects.create(
        market=market,
        product=product,
        value=Decimal("100.00"),
        weighted_distribution=None,
        date=date(2016, 9, 4),
        period_weeks=4,
    )
    data.refresh_from_db()
    assert data.weighted_distribution is None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && pytest market_data/tests/test_models.py::test_data_weighted_distribution_can_be_null -v
```

Expected: FAIL — Django raises `IntegrityError` or `django.db.utils.IntegrityError` because the column is `NOT NULL`.

- [ ] **Step 3: Update the model field**

In `backend/market_data/models.py`, change line 39:

```python
# Before
weighted_distribution = models.DecimalField(max_digits=5, decimal_places=2)

# After
weighted_distribution = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
```

- [ ] **Step 4: Generate the migration**

```bash
cd backend && python manage.py makemigrations
```

Expected output:
```
Migrations for 'market_data':
  market_data/migrations/0004_alter_data_weighted_distribution_nullable.py
    - Alter field weighted_distribution on data
```

Verify the generated file looks like:

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('market_data', '0003_alter_data_weighted_distribution'),
    ]
    operations = [
        migrations.AlterField(
            model_name='data',
            name='weighted_distribution',
            field=models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True),
        ),
    ]
```

- [ ] **Step 5: Run all model tests to verify they pass**

```bash
cd backend && pytest market_data/tests/test_models.py -v
```

Expected: all tests PASS — the new null test and all existing tests including `test_data_links_market_and_product` (which still uses `Decimal("85.85")`, a valid non-null value).

- [ ] **Step 6: Commit**

```bash
git add backend/market_data/models.py \
        backend/market_data/migrations/0004_alter_data_weighted_distribution_nullable.py \
        backend/market_data/tests/test_models.py
git commit -m "feat: allow Data.weighted_distribution to be NULL"
```

---

### Task 2: Loader + load_csv tests

**Files:**
- Modify: `backend/market_data/management/commands/load_csv.py`
- Modify: `backend/market_data/tests/test_load_csv.py`

- [ ] **Step 1: Add a failing test for empty WTD**

Append this test to `backend/market_data/tests/test_load_csv.py` (all needed imports already exist at the top of the file):

```python
@pytest.mark.django_db
def test_empty_wtd_stores_null(write_csv):
    row = "MARKET3,1000,,CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400,ITEM,CHS,ORGANIC TREE,UT PLUS,UT VETO BRETS,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
    filename = write_csv("test_empty_wtd.csv", "\n".join([CSV_HEADER, row]))
    call_command("load_csv", filename)
    data_row = Data.objects.get(
        product__description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400"
    )
    assert data_row.weighted_distribution is None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && pytest market_data/tests/test_load_csv.py::test_empty_wtd_stores_null -v
```

Expected: FAIL — the loader currently runs `Decimal(row["WTD"])` on an empty string which raises `InvalidOperation`, caught and re-raised as `ValueError("Cannot parse weighted_distribution from WTD: ''")`.

- [ ] **Step 3: Update the loader**

In `backend/market_data/management/commands/load_csv.py`, replace the WTD parsing block (lines 77–80):

```python
# Before
try:
    weighted_distribution = Decimal(row["WTD"])
except InvalidOperation:
    raise ValueError(f"Cannot parse weighted_distribution from WTD: {row['WTD']!r}")

# After
wtd_raw = row["WTD"].strip()
if wtd_raw:
    try:
        weighted_distribution = Decimal(wtd_raw)
    except InvalidOperation:
        raise ValueError(f"Cannot parse weighted_distribution from WTD: {row['WTD']!r}")
else:
    weighted_distribution = None
```

`Decimal` and `InvalidOperation` are already imported at the top of the file — no new imports needed.

- [ ] **Step 4: Run the new test to verify it passes**

```bash
cd backend && pytest market_data/tests/test_load_csv.py::test_empty_wtd_stores_null -v
```

Expected: PASS.

- [ ] **Step 5: Run all tests to verify no regressions**

```bash
cd backend && pytest market_data/tests/ -v
```

Expected: all tests PASS — including `test_invalid_wtd_rolls_back` (non-empty invalid WTD still raises `ValueError`).

- [ ] **Step 6: Commit**

```bash
git add backend/market_data/management/commands/load_csv.py \
        backend/market_data/tests/test_load_csv.py
git commit -m "feat: store NULL for empty WTD instead of raising an error"
```
