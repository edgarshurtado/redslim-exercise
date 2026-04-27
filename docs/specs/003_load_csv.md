# Spec 003 — Load CSV

Django management command that imports a retail sales CSV file into the database, mapping CSV columns to the five models defined in spec 002.

---

## CSV Format

Header row:

```
M Desc,VAL,WTD,Product,LEVEL,CATEGORY,MANUFACTURER,BRAND,SUBBRAND,SEGMENT,PACKSIZE,SIZE,FORMAT,TIME,M Desc 2,DATETIME
```

Relevant columns:

| Column | Description |
|---|---|
| `M Desc` | Primary market identifier (e.g. `"MARKET3"`) |
| `M Desc 2` | Secondary market / retailer description (e.g. `"TOT RETAILER 1"`) |
| `VAL` | Sales value (integer) |
| `WTD` | Weighted distribution × 100 (e.g. `9400` = 94%) |
| `Product` | Full product description |
| `BRAND` | Brand name |
| `SUBBRAND` | Sub-brand name |
| `TIME` | Period code containing week count (e.g. `"AUG16 4WKS 04/09/16"`) |
| `DATETIME` | Reporting period end date in `YYYY-MM-DD` format |

---

## Command

**Location:** `backend/market_data/management/commands/load_csv.py`

**Invocation:**
```
python manage.py load_csv <filename>
```

`<filename>` is the file name only (e.g. `sales.csv`). The command resolves the full path as `docs/data/<filename>` relative to the project root (one level above `backend/`).

**Output:** A summary line printed to stdout on success:
```
Loaded X rows from <filename>.
```

`X` is the count of newly created `Data` rows (rows already present are not counted).

---

## Processing Logic

The entire import runs inside a single `transaction.atomic()` block. Any exception aborts and rolls back all changes.

### Dimension Caching

Before hitting the database, each dimension lookup checks an in-memory dict keyed by the dimension's natural key. On a cache miss the command calls `get_or_create` and stores the result. This prevents redundant queries for repeated dimension values across rows.

One cache dict per dimension:

- `brand_cache`: keyed by `(description,)`
- `sub_brand_cache`: keyed by `(description, brand_id)`
- `product_cache`: keyed by `(description, sub_brand_id)`
- `market_cache`: keyed by `(description, description_2)`

`Data` rows are not cached.

### Per-Row Processing Order

FK dependencies are resolved bottom-up before inserting `Data`:

1. **Brand** — `get_or_create(description=BRAND)`
2. **SubBrand** — `get_or_create(description=SUBBRAND, brand=brand)`
3. **Product** — `get_or_create(description=Product, sub_brand=sub_brand)`
4. **Market** — `get_or_create(description=M Desc, description_2=M Desc 2)`
5. **Data** — `get_or_create(market=market, product=product, date=DATETIME)` with `defaults={value, weighted_distribution, period_weeks}`

### Field Derivations

| Model field | Source | Transformation |
|---|---|---|
| `Data.value` | `VAL` | `int(row['VAL'])` |
| `Data.weighted_distribution` | `WTD` | `int(row['WTD'])` |
| `Data.date` | `DATETIME` | `datetime.date.fromisoformat(row['DATETIME'])` |
| `Data.period_weeks` | `TIME` | `int(re.search(r'(\d+)WKS', row['TIME']).group(1))` — raises `ValueError` if no match |

---

## Error Handling

| Condition | Behaviour |
|---|---|
| File not found | Command raises `CommandError` before opening the DB transaction |
| `TIME` column has no `WKS` pattern | `ValueError` propagates; transaction rolls back |
| Any other exception during import | Exception propagates; transaction rolls back |

All errors are all-or-nothing — no partial imports.

---

## Acceptance Criteria

1. `python manage.py load_csv <filename>` loads all rows from `docs/data/<filename>` into the database.
2. Running the command twice on the same file produces identical row counts (no duplicates in any table).
3. A shared `BRAND` value across multiple rows results in a single `Brand` row.
4. `Data` rows are unique on `(market, product, date)`.
5. A CSV with an invalid `TIME` column (no `WKS` pattern) aborts with no rows persisted.
6. A non-existent filename raises a clear error before touching the database.

---

## Tests

**Location:** `backend/market_data/tests/test_load_csv.py`

| # | Name | What it verifies |
|---|---|---|
| 1 | Happy path | Load 3–5 row fixture; assert correct counts in all five tables and spot-check field values |
| 2 | Idempotency | Run command twice; assert row counts are identical after second run and second run stdout reports `Loaded 0 rows` |
| 3 | Dimension deduplication | Two rows with same `BRAND`; assert only one `Brand` row exists |
| 4 | Cache effectiveness | N rows sharing all dimension values; use `CaptureQueriesContext` to assert query count == 28 (4 dim SELECT+INSERT on first row only, + N × 2 Data SELECT+INSERT) |
| 5 | Invalid TIME | Row with no `WKS` in `TIME`; assert error raised and all tables empty (full rollback) |
| 6 | File not found | Non-existent filename; assert `CommandError` raised |
