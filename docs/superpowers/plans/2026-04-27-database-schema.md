# Database Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `market_data` Django app with five normalized models (Brand, SubBrand, Product, Market, Data) and apply migrations to PostgreSQL.

**Architecture:** A single new Django app `market_data` holds all five models in one `models.py`. FK relationships cascade on delete. Tests use `pytest-django` with `@pytest.mark.django_db`, hitting the real database — no mocking.

**Tech Stack:** Django 5, pytest-django, PostgreSQL (psycopg2-binary)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `backend/market_data/__init__.py` | App package marker |
| Create | `backend/market_data/apps.py` | App config |
| Create | `backend/market_data/models.py` | All 5 models |
| Create | `backend/market_data/migrations/__init__.py` | Migrations package marker |
| Create | `backend/market_data/tests/__init__.py` | Test package marker |
| Create | `backend/market_data/tests/test_models.py` | Model tests |
| Modify | `backend/redslim/settings.py` | Register `market_data` in INSTALLED_APPS |

---

## Task 1: Bootstrap the `market_data` app

**Files:**
- Create: `backend/market_data/__init__.py`
- Create: `backend/market_data/apps.py`
- Create: `backend/market_data/models.py`
- Create: `backend/market_data/migrations/__init__.py`
- Create: `backend/market_data/tests/__init__.py`
- Modify: `backend/redslim/settings.py`

- [ ] **Step 1: Create the app directory and empty files**

```bash
mkdir -p backend/market_data/migrations
mkdir -p backend/market_data/tests
touch backend/market_data/__init__.py
touch backend/market_data/migrations/__init__.py
touch backend/market_data/tests/__init__.py
```

- [ ] **Step 2: Create `backend/market_data/apps.py`**

```python
from django.apps import AppConfig


class MarketDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'market_data'
```

- [ ] **Step 3: Create an empty `backend/market_data/models.py`**

```python
from django.db import models
```

- [ ] **Step 4: Register the app in `backend/redslim/settings.py`**

In the `INSTALLED_APPS` list, add `'market_data.apps.MarketDataConfig'` after `'hello.apps.HelloConfig'`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'hello.apps.HelloConfig',
    'market_data.apps.MarketDataConfig',
]
```

- [ ] **Step 5: Verify Django can load the app**

Run from `backend/`:
```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
git add backend/market_data/ backend/redslim/settings.py
git commit -m "chore: bootstrap market_data app"
```

---

## Task 2: Write failing model tests

**Files:**
- Create: `backend/market_data/tests/test_models.py`

- [ ] **Step 1: Create `backend/market_data/tests/test_models.py`**

```python
import pytest
from datetime import date
from market_data.models import Brand, SubBrand, Product, Market, Data


@pytest.mark.django_db
def test_brand_can_be_created():
    brand = Brand.objects.create(description="UT PLUS")
    assert brand.id is not None
    assert brand.description == "UT PLUS"


@pytest.mark.django_db
def test_subbrand_belongs_to_brand():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    assert subbrand.brand_id == brand.id


@pytest.mark.django_db
def test_subbrand_cascades_on_brand_delete():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    brand.delete()
    assert not SubBrand.objects.filter(id=subbrand.id).exists()


@pytest.mark.django_db
def test_product_belongs_to_subbrand():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    product = Product.objects.create(
        description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400",
        sub_brand=subbrand,
    )
    assert product.sub_brand_id == subbrand.id


@pytest.mark.django_db
def test_product_cascades_on_subbrand_delete():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    product = Product.objects.create(
        description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400",
        sub_brand=subbrand,
    )
    subbrand.delete()
    assert not Product.objects.filter(id=product.id).exists()


@pytest.mark.django_db
def test_market_can_be_created():
    market = Market.objects.create(description="MARKET3", description_2="TOT RETAILER 1")
    assert market.id is not None
    assert market.description == "MARKET3"
    assert market.description_2 == "TOT RETAILER 1"


@pytest.mark.django_db
def test_data_links_market_and_product():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    product = Product.objects.create(
        description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400",
        sub_brand=subbrand,
    )
    market = Market.objects.create(description="MARKET3", description_2="TOT RETAILER 1")
    data = Data.objects.create(
        market=market,
        product=product,
        value=32,
        weighted_distribution=9400,
        date=date(2016, 9, 4),
        period_weeks=4,
    )
    assert data.id is not None
    assert data.value == 32
    assert data.weighted_distribution == 9400
    assert data.period_weeks == 4


@pytest.mark.django_db
def test_data_cascades_on_market_delete():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    product = Product.objects.create(
        description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400",
        sub_brand=subbrand,
    )
    market = Market.objects.create(description="MARKET3", description_2="TOT RETAILER 1")
    data = Data.objects.create(
        market=market,
        product=product,
        value=32,
        weighted_distribution=9400,
        date=date(2016, 9, 4),
        period_weeks=4,
    )
    market.delete()
    assert not Data.objects.filter(id=data.id).exists()


@pytest.mark.django_db
def test_data_cascades_on_product_delete():
    brand = Brand.objects.create(description="UT PLUS")
    subbrand = SubBrand.objects.create(description="UT VETO BRETS", brand=brand)
    product = Product.objects.create(
        description="CHS ORGANIC TREE UT PLUS UT VETO BRETS FAMILY 400",
        sub_brand=subbrand,
    )
    market = Market.objects.create(description="MARKET3", description_2="TOT RETAILER 1")
    data = Data.objects.create(
        market=market,
        product=product,
        value=32,
        weighted_distribution=9400,
        date=date(2016, 9, 4),
        period_weeks=4,
    )
    product.delete()
    assert not Data.objects.filter(id=data.id).exists()
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run from `backend/`:
```bash
pytest market_data/tests/test_models.py -v
```
Expected: All 9 tests fail with `ImportError` or `django.db.utils.ProgrammingError` (models not defined yet).

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/tests/test_models.py
git commit -m "test: add failing model tests for market_data schema"
```

---

## Task 3: Implement the five models

**Files:**
- Modify: `backend/market_data/models.py`

- [ ] **Step 1: Write all five models in `backend/market_data/models.py`**

```python
from django.db import models


class Brand(models.Model):
    description = models.CharField(max_length=255)

    class Meta:
        db_table = 'brand'


class SubBrand(models.Model):
    description = models.CharField(max_length=255)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, db_column='brand_fk')

    class Meta:
        db_table = 'subbrand'


class Product(models.Model):
    description = models.CharField(max_length=500)
    sub_brand = models.ForeignKey(SubBrand, on_delete=models.CASCADE, db_column='sub_brand_fk')

    class Meta:
        db_table = 'product'


class Market(models.Model):
    description = models.CharField(max_length=255)
    description_2 = models.CharField(max_length=255)

    class Meta:
        db_table = 'market'


class Data(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, db_column='market_fk')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_fk')
    value = models.IntegerField()
    weighted_distribution = models.IntegerField()
    date = models.DateField()
    period_weeks = models.IntegerField()

    class Meta:
        db_table = 'sales_data'
```

- [ ] **Step 2: Verify Django accepts the models**

Run from `backend/`:
```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/models.py
git commit -m "feat: implement Brand, SubBrand, Product, Market, Data models"
```

---

## Task 4: Generate and apply migrations

**Files:**
- Create: `backend/market_data/migrations/0001_initial.py` (auto-generated)

- [ ] **Step 1: Generate the migration**

Run from `backend/`:
```bash
python manage.py makemigrations market_data
```
Expected output:
```
Migrations for 'market_data':
  market_data/migrations/0001_initial.py
    - Create model Brand
    - Create model Market
    - Create model SubBrand
    - Create model Product
    - Create model Data
```

- [ ] **Step 2: Apply the migration**

```bash
python manage.py migrate market_data
```
Expected: Migration applies cleanly with no errors.

- [ ] **Step 3: Commit**

```bash
git add backend/market_data/migrations/0001_initial.py
git commit -m "feat: add initial migration for market_data schema"
```

---

## Task 5: Run tests and verify all pass

- [ ] **Step 1: Run the full market_data test suite**

Run from `backend/`:
```bash
pytest market_data/tests/test_models.py -v
```
Expected: All 9 tests pass:
```
PASSED test_brand_can_be_created
PASSED test_subbrand_belongs_to_brand
PASSED test_subbrand_cascades_on_brand_delete
PASSED test_product_belongs_to_subbrand
PASSED test_product_cascades_on_subbrand_delete
PASSED test_market_can_be_created
PASSED test_data_links_market_and_product
PASSED test_data_cascades_on_market_delete
PASSED test_data_cascades_on_product_delete
```

- [ ] **Step 2: Run the full backend test suite to check for regressions**

```bash
pytest -v
```
Expected: All tests pass including the pre-existing `hello` tests.
