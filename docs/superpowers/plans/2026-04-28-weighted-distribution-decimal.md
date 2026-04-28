# weighted_distribution: int → decimal(5,2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change `Data.weighted_distribution` from `IntegerField` to `DecimalField(max_digits=5, decimal_places=2)` so WTD is stored as a raw percentage (e.g. `85.85`) instead of an integer.

**Architecture:** Two-step TDD change — model + migration first, then loader. Existing test rows use fabricated WTD integers (9400, 8500, 7500) from the old "× 100" convention; those values must be replaced with realistic percentages (94.00, 85.00, 75.00) as part of this change.

**Tech Stack:** Django ORM (`DecimalField`), pytest-django, Python `decimal.Decimal`

---

## Files

- Modify: `backend/market_data/models.py:39`
- Create: `backend/market_data/migrations/0003_alter_data_weighted_distribution.py` (via `makemigrations`)
- Modify: `backend/market_data/tests/test_models.py:20,82`
- Modify: `backend/market_data/management/commands/load_csv.py:83`
- Modify: `backend/market_data/tests/test_load_csv.py` (rows + assertions)

---

### Task 1: Model field + migration

**Files:**
- Modify: `backend/market_data/models.py:39`
- Create: `backend/market_data/migrations/0003_alter_data_weighted_distribution.py`
- Modify: `backend/market_data/tests/test_models.py:20,82`

- [ ] **Step 1: Update test_models.py to use Decimal for weighted_distribution**

In `backend/market_data/tests/test_models.py`, change the fixture (line 20) and the assertion (line 82):

```python
# fixture — change weighted_distribution from 9400 to Decimal("85.85")
return Data.objects.create(
    market=market,
    product=product,
    value=Decimal("32.40"),
    weighted_distribution=Decimal("85.85"),
    date=date(2016, 9, 4),
    period_weeks=4,
)

# assertion in test_data_links_market_and_product — change line 82
assert data_record.weighted_distribution == Decimal("85.85")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest market_data/tests/test_models.py::test_data_links_market_and_product -v
```

Expected: FAIL — `assert Decimal('85.85') == 9400` (model still IntegerField, stores 85 after truncation, or raises ValidationError depending on DB strictness).

- [ ] **Step 3: Change the model field**

In `backend/market_data/models.py`, change line 39:

```python
# Before
weighted_distribution = models.IntegerField()

# After
weighted_distribution = models.DecimalField(max_digits=5, decimal_places=2)
```

- [ ] **Step 4: Generate the migration**

```bash
cd backend && python manage.py makemigrations
```

Expected output:
```
Migrations for 'market_data':
  market_data/migrations/0003_alter_data_weighted_distribution.py
    - Alter field weighted_distribution on data
```

Verify the generated file looks like:

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('market_data', '0002_alter_data_value'),
    ]
    operations = [
        migrations.AlterField(
            model_name='data',
            name='weighted_distribution',
            field=models.DecimalField(decimal_places=2, max_digits=5),
        ),
    ]
```

- [ ] **Step 5: Run all model tests to verify they pass**

```bash
cd backend && pytest market_data/tests/test_models.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/market_data/models.py \
        backend/market_data/migrations/0003_alter_data_weighted_distribution.py \
        backend/market_data/tests/test_models.py
git commit -m "feat: store Data.weighted_distribution as decimal(5,2) instead of int"
```

---

### Task 2: Loader + load_csv tests

**Files:**
- Modify: `backend/market_data/management/commands/load_csv.py:83`
- Modify: `backend/market_data/tests/test_load_csv.py`

- [ ] **Step 1: Update module-level row constants in test_load_csv.py**

Replace the WTD column (3rd field) in all four row constants. The old integer values (9400, 8500, 7500) were a fabricated "× 100" convention; replace with raw percentages.

```python
# Before
ROW_1 = "MARKET3,1000,9400,CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400,ITEM,CHS,ORGANIC TREE,UT PLUS,UT VETO BRETS,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
ROW_2 = "MARKET3,2000,8500,CHS SUPER FOOD SON WIIT-PEX CAYNTGAWN ADULT 500,ITEM,CHS,SUPER FOOD,SON WIIT-PEX,CAYNTGAWN,ADULT,500-599G,500.0,SHREDDED/GRATED,AUG16 4WKS 04/09/16,TOT RETAILER 2,2016-09-04"
ROW_3 = "MARKET4,3000,7500,CHS PRIVATE LABEL PL-SUB FAMILY 300,ITEM,CHS,PRIVATE LABEL,PRIVATE LABEL,PL-SUB,FAMILY,300-399G,300.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
ROW_DECIMAL = "MARKET3,32.40,9400,CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400,ITEM,CHS,ORGANIC TREE,UT PLUS,UT VETO BRETS,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"

# After
ROW_1 = "MARKET3,1000,94.00,CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400,ITEM,CHS,ORGANIC TREE,UT PLUS,UT VETO BRETS,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
ROW_2 = "MARKET3,2000,85.00,CHS SUPER FOOD SON WIIT-PEX CAYNTGAWN ADULT 500,ITEM,CHS,SUPER FOOD,SON WIIT-PEX,CAYNTGAWN,ADULT,500-599G,500.0,SHREDDED/GRATED,AUG16 4WKS 04/09/16,TOT RETAILER 2,2016-09-04"
ROW_3 = "MARKET4,3000,75.00,CHS PRIVATE LABEL PL-SUB FAMILY 300,ITEM,CHS,PRIVATE LABEL,PRIVATE LABEL,PL-SUB,FAMILY,300-399G,300.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
ROW_DECIMAL = "MARKET3,32.40,94.00,CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400,ITEM,CHS,ORGANIC TREE,UT PLUS,UT VETO BRETS,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
```

- [ ] **Step 2: Update weighted_distribution assertion in test_happy_path**

In `test_happy_path`, change the spot-check for `weighted_distribution` (the row comes from ROW_1, which now has WTD=94.00):

```python
# Before
assert data_row.weighted_distribution == 9400

# After
assert data_row.weighted_distribution == Decimal("94.00")
```

- [ ] **Step 3: Update inline WTD values in remaining test functions**

In `test_dimension_deduplication`, update the two inline row strings:

```python
# Before
row_a = "MARKET3,1000,9400,PRODUCT ALPHA,ITEM,CHS,MFG,SHARED BRAND,SHARED SUB,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
row_b = "MARKET3,2000,8500,PRODUCT BETA,ITEM,CHS,MFG,SHARED BRAND,SHARED SUB,ADULT,400-499G,400.0,CHUNKY,AUG16 4WKS 11/09/16,TOT RETAILER 1,2016-09-11"

# After
row_a = "MARKET3,1000,94.00,PRODUCT ALPHA,ITEM,CHS,MFG,SHARED BRAND,SHARED SUB,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
row_b = "MARKET3,2000,85.00,PRODUCT BETA,ITEM,CHS,MFG,SHARED BRAND,SHARED SUB,ADULT,400-499G,400.0,CHUNKY,AUG16 4WKS 11/09/16,TOT RETAILER 1,2016-09-11"
```

In `test_cache_effectiveness`, update the row template inside the list comprehension:

```python
# Before
rows = [
    f"MARKET3,1000,9400,SAME PRODUCT,ITEM,CHS,MFG,SAME BRAND,SAME SUB,FAMILY,400-499G,400.0,CHUNKY,{time},TOT RETAILER 1,{iso}"
    for time, iso in dates
]

# After
rows = [
    f"MARKET3,1000,94.00,SAME PRODUCT,ITEM,CHS,MFG,SAME BRAND,SAME SUB,FAMILY,400-499G,400.0,CHUNKY,{time},TOT RETAILER 1,{iso}"
    for time, iso in dates
]
```

In `test_invalid_time_rolls_back`, update the two inline row strings:

```python
# Before
valid_row = "MARKET3,1000,9400,PRODUCT VALID,ITEM,CHS,MFG,BRAND VALID,SUB VALID,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
invalid_row = "MARKET3,2000,8500,PRODUCT INVALID,ITEM,CHS,MFG,BRAND INVALID,SUB INVALID,FAMILY,400-499G,400.0,CHUNKY,AUG16 BADTIME,TOT RETAILER 1,2016-09-04"

# After
valid_row = "MARKET3,1000,94.00,PRODUCT VALID,ITEM,CHS,MFG,BRAND VALID,SUB VALID,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
invalid_row = "MARKET3,2000,85.00,PRODUCT INVALID,ITEM,CHS,MFG,BRAND INVALID,SUB INVALID,FAMILY,400-499G,400.0,CHUNKY,AUG16 BADTIME,TOT RETAILER 1,2016-09-04"
```

- [ ] **Step 4: Run the load_csv tests to verify they fail**

```bash
cd backend && pytest market_data/tests/test_load_csv.py -v
```

Expected: multiple FAILs — `assert Decimal('94.00') == 9400` (loader still calls `int(row["WTD"])`).

- [ ] **Step 5: Update the loader**

In `backend/market_data/management/commands/load_csv.py`, change the `defaults` dict (line 83):

```python
# Before
defaults={
    "value": value,
    "weighted_distribution": int(row["WTD"]),
    "period_weeks": int(match.group(1)),
},

# After
defaults={
    "value": value,
    "weighted_distribution": Decimal(row["WTD"]),
    "period_weeks": int(match.group(1)),
},
```

`Decimal` is already imported at the top of the file — no new import needed.

- [ ] **Step 6: Run all tests to verify they pass**

```bash
cd backend && pytest market_data/tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/market_data/management/commands/load_csv.py \
        backend/market_data/tests/test_load_csv.py
git commit -m "feat: parse Data.weighted_distribution as Decimal instead of int"
```
