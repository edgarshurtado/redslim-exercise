# Data.value → DecimalField Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change `Data.value` from `IntegerField` to `DecimalField(max_digits=12, decimal_places=2)` so that sales values like `32.40` are stored exactly without truncation.

**Architecture:** Update the Django model, generate a migration, and fix the CSV loader to parse `VAL` as `Decimal` instead of `int`. Existing tests are updated for type correctness. A new test is added first (TDD) to drive the change.

**Tech Stack:** Django 5.x, PostgreSQL, pytest-django. All commands run from `backend/`.

---

## Files

| File | Action | Purpose |
|---|---|---|
| `backend/market_data/tests/test_load_csv.py` | Modify | Add failing decimal test; update int assertions to `Decimal` |
| `backend/market_data/tests/test_models.py` | Modify | Update fixture and assertion to use `Decimal` |
| `backend/market_data/models.py` | Modify | `IntegerField` → `DecimalField(max_digits=12, decimal_places=2)` |
| `backend/market_data/migrations/0002_alter_data_value.py` | Create (generated) | Migration for column type change |
| `backend/market_data/management/commands/load_csv.py` | Modify | `int(row["VAL"])` → `Decimal(row["VAL"])` |

---

## Task 1: Write a failing test for decimal VAL storage

**Files:**
- Modify: `backend/market_data/tests/test_load_csv.py`

- [ ] **Step 1: Add a decimal row constant and a new test**

At the top of `test_load_csv.py`, after `ROW_3`, add:

```python
ROW_DECIMAL = "MARKET3,32.40,9400,CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400,ITEM,CHS,ORGANIC TREE,UT PLUS,UT VETO BRETS,FAMILY,400-499G,400.0,CHUNKY,AUG16 4WKS 04/09/16,TOT RETAILER 1,2016-09-04"
```

At the end of `test_load_csv.py`, add:

```python
@pytest.mark.django_db
def test_decimal_value_is_stored_exactly(write_csv):
    from decimal import Decimal
    filename = write_csv("test_decimal.csv", "\n".join([CSV_HEADER, ROW_DECIMAL]))
    call_command("load_csv", filename)
    data_row = Data.objects.get(
        product__description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400"
    )
    assert data_row.value == Decimal("32.40")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /home/rumil/repos/redslim-exercise/backend
pytest market_data/tests/test_load_csv.py::test_decimal_value_is_stored_exactly -v
```

Expected: **FAIL** — `ValueError: invalid literal for int() with base 10: '32.40'`

---

## Task 2: Update the model and generate the migration

**Files:**
- Modify: `backend/market_data/models.py`
- Create: `backend/market_data/migrations/0002_alter_data_value.py` (generated)

- [ ] **Step 1: Update the model field**

In `backend/market_data/models.py`, change line 38:

```python
# before
value = models.IntegerField()

# after
value = models.DecimalField(max_digits=12, decimal_places=2)
```

- [ ] **Step 2: Generate the migration**

```bash
cd /home/rumil/repos/redslim-exercise/backend
python manage.py makemigrations market_data --name alter_data_value
```

Expected output:
```
Migrations for 'market_data':
  market_data/migrations/0002_alter_data_value.py
    - Alter field value on data
```

- [ ] **Step 3: Verify the migration file looks correct**

```bash
cat market_data/migrations/0002_alter_data_value.py
```

The file should contain `migrations.AlterField` for `value` with `models.DecimalField(decimal_places=2, max_digits=12)`.

---

## Task 3: Update the loader to parse VAL as Decimal

**Files:**
- Modify: `backend/market_data/management/commands/load_csv.py`

- [ ] **Step 1: Add the Decimal import**

At the top of `load_csv.py`, after `import re`, add:

```python
from decimal import Decimal
```

- [ ] **Step 2: Change the VAL conversion**

In the `get_or_create` defaults dict (around line 76), change:

```python
# before
"value": int(row["VAL"]),

# after
"value": Decimal(row["VAL"]),
```

- [ ] **Step 3: Run the new test to verify it passes**

```bash
cd /home/rumil/repos/redslim-exercise/backend
pytest market_data/tests/test_load_csv.py::test_decimal_value_is_stored_exactly -v
```

Expected: **PASS**

---

## Task 4: Update existing test assertions to use Decimal

**Files:**
- Modify: `backend/market_data/tests/test_load_csv.py`
- Modify: `backend/market_data/tests/test_models.py`

- [ ] **Step 1: Update the happy path assertion in test_load_csv.py**

In `test_happy_path`, change:

```python
# before
assert data_row.value == 1000

# after
from decimal import Decimal
assert data_row.value == Decimal("1000")
```

Add the import at the top of the function (or at module level — module level preferred):

```python
from decimal import Decimal
```

Add this at the top of `test_load_csv.py` (after the existing imports):

```python
from decimal import Decimal
```

Then update the assertion in `test_happy_path`:

```python
assert data_row.value == Decimal("1000")
```

- [ ] **Step 2: Update the data_record fixture and assertion in test_models.py**

Add import at the top of `test_models.py` (after existing imports):

```python
from decimal import Decimal
```

In the `data_record` fixture, change:

```python
# before
value=32,

# after
value=Decimal("32.40"),
```

In `test_data_links_market_and_product`, change:

```python
# before
assert data_record.value == 32

# after
assert data_record.value == Decimal("32.40")
```

- [ ] **Step 3: Run the full test suite**

```bash
cd /home/rumil/repos/redslim-exercise/backend
pytest market_data/ -v
```

Expected: **all tests PASS** — no failures, no errors.

---

## Task 5: Commit

- [ ] **Step 1: Stage and commit**

```bash
git add backend/market_data/models.py \
        backend/market_data/migrations/0002_alter_data_value.py \
        backend/market_data/management/commands/load_csv.py \
        backend/market_data/tests/test_load_csv.py \
        backend/market_data/tests/test_models.py
git commit -m "feat: store Data.value as decimal(12,2) instead of int"
```
