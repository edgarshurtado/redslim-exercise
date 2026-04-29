# Spec 008 — Load Parquet

Django management command that imports a retail-sales **parquet dataset** (a folder of five files) into the database, mapping parquet columns to the same five models used by `load_csv` (spec 003).

The data file is large (~2.5 M rows in the reference dataset), so the loader uses **bulk inserts with `ON CONFLICT DO NOTHING`** rather than per-row `get_or_create`. Companion files (markets, periods, products) are small enough to load entirely into memory and resolve foreign keys via in-memory dicts.

---

## Input layout

The command accepts a folder name. The folder lives under `docs/data/<foldername>/` and contains five parquet files that share a common prefix and differ only by suffix:

| Suffix | Contents | Used? |
|---|---|---|
| `*_data.parquet` | Fact rows (`MARKET_TAG`, `PRODUCT_TAG`, `PERIOD_TAG`, `VAL`, `VOL`, `UNI`, `WTD`) | Yes |
| `*_mkt.parquet` | Market dimension | Yes |
| `*_per.parquet` | Period dimension | Yes |
| `*_prod.parquet` | Product dimension | Yes |
| `*_fct.parquet` | Fact-column metadata | **Ignored** |

Required columns per file:

- **`*_data.parquet`** — `MARKET_TAG`, `PRODUCT_TAG`, `PERIOD_TAG`, `VAL`, `WTD` (other columns ignored).
- **`*_mkt.parquet`** — `TAG`, `SHORT`, `LONG`.
- **`*_per.parquet`** — `TAG`, `DATETIME`.
- **`*_prod.parquet`** — `TAG`, `SDESC`, `LEVEL`, `GL Brand`, `GL Sub Brand`.

---

## Command

**Location:** `backend/market_data/management/commands/load_parquet.py`

**Invocation:**
```
python manage.py load_parquet <foldername>
```

`<foldername>` is a folder name only (e.g. `unistar_dk`). The command resolves the path as `docs/data/<foldername>/` relative to the project root (mirrors `load_csv`).

**Output (success):**
```
Loaded X rows from <foldername>.
```
where `X` is the number of newly created `Data` rows, computed as `Data.objects.count()` after minus before.

---

## Dependencies

`pyarrow` is added to `backend/requirements.txt`. (`pandas` is already a dependency; pandas needs an engine to read parquet.)

---

## Migration

A new migration on `market_data` adds unique constraints to all five tables, mirroring the natural keys the existing `load_csv` already uses via `get_or_create`:

| Model | Unique constraint name | Fields |
|---|---|---|
| `Brand` | `uniq_brand_description` | `description` |
| `SubBrand` | `uniq_subbrand_description_brand` | `description`, `brand` |
| `Product` | `uniq_product_description_subbrand` | `description`, `sub_brand` |
| `Market` | `uniq_market_descriptions` | `description`, `description_2` |
| `Data` | `uniq_data_market_product_date` | `market`, `product`, `date` |

These constraints unblock `bulk_create(ignore_conflicts=True)` (Postgres `INSERT … ON CONFLICT DO NOTHING`) on every table and let the loader refetch dimension rows by natural key after insert. The existing `load_csv` semantics are unaffected — its `get_or_create` calls already obeyed these uniqueness rules. (If a database somehow contains duplicate dimension rows from before the migration, the migration will fail and a manual de-dup is required first; in practice no existing loader produces duplicates.)

---

## Processing logic

The entire import runs inside a single `transaction.atomic()` block. Any exception aborts and rolls back **all** changes (matches `load_csv` semantics).

### Phase 1 — Dimensions (in-memory → bulk insert)

Read the four companion files with `pandas.read_parquet`.

#### Products (`*_prod.parquet`)

Filter to leaf level only:
```python
LEAF_LEVEL = "MANUFACTURER!SEGMENT!SUB SEGMENT!BRAND!SUB BRAND!PROMO/NON PROMO!SIZE!ITEM"
prod_df = prod_df[prod_df["LEVEL"] == LEAF_LEVEL]
```

Then, in dependency order. After every dimension `bulk_create`, the loader **refetches** the dimension's rows and builds a `natural_key → id` dict — this works correctly on first runs and on re-runs (where `ignore_conflicts=True` skips already-existing rows).

1. **Brand** — `Brand.objects.bulk_create([Brand(description=b) for b in set(prod_df["GL Brand"])], ignore_conflicts=True)`. Refetch with `Brand.objects.in_bulk(field_name='description')` → `brand_id_by_desc: dict[str → id]`.
2. **SubBrand** — for each `(GL Sub Brand, GL Brand)` pair in the de-duplicated set, build `SubBrand(description=sub, brand_id=brand_id_by_desc[brand])`. `bulk_create(..., ignore_conflicts=True)`. Refetch all `SubBrand` rows whose `brand_id` is in `brand_id_by_desc.values()` and build `subbrand_id_by_pair: dict[(description, brand_id) → id]`.
3. **Product** — one instance per `prod_df` row: `Product(description=row.SDESC, sub_brand_id=subbrand_id_by_pair[(row['GL Sub Brand'], brand_id_by_desc[row['GL Brand']])])`. `bulk_create(..., ignore_conflicts=True)`. Refetch all `Product` rows whose `sub_brand_id` is in `subbrand_id_by_pair.values()` and build `product_id_by_natural_key: dict[(description, sub_brand_id) → id]`. Then build `product_id_by_tag: dict[TAG → id]` by walking `prod_df` and looking up each row's `(SDESC, sub_brand_id)`. (When two `prod.TAG` rows share the same `(SDESC, sub_brand_id)` they collapse to the same `Product.id` — same semantics as `load_csv`.)

#### Markets (`*_mkt.parquet`)

No `LEVEL` filter (all rows ingested — including hierarchy aggregates such as `TOTAL DENMARK`; data rows reference markets explicitly so there is no double-counting risk).

For each row in `mkt_df`: `Market(description=row.SHORT, description_2=row.LONG)`. `bulk_create(..., ignore_conflicts=True)`. Refetch into `market_id_by_natural_key: dict[(description, description_2) → id]`, then build `market_id_by_tag: dict[TAG → id]` by walking `mkt_df` and looking up each row's `(SHORT, LONG)`.

#### Periods (`*_per.parquet`)

No DB write. Build `date_by_tag: dict[TAG → datetime.date]` directly from the DataFrame (`DATETIME` is already a `datetime.date`).

### Phase 2 — Data (streamed bulk insert)

Capture `count_before = Data.objects.count()` immediately before the loop. Then stream `*_data.parquet` in chunks using `pyarrow.parquet.ParquetFile.iter_batches(batch_size=50_000)`. For each batch:

```python
df = batch.to_pandas()
df = df.dropna(subset=["VAL"])
df = df[df["MARKET_TAG"].isin(market_id_by_tag)]
df = df[df["PRODUCT_TAG"].isin(product_id_by_tag)]   # drops non-leaf products
df = df[df["PERIOD_TAG"].isin(date_by_tag)]
rows = [
    Data(
        market_id=market_id_by_tag[r.MARKET_TAG],
        product_id=product_id_by_tag[r.PRODUCT_TAG],
        date=date_by_tag[r.PERIOD_TAG],
        value=Decimal(r.VAL * 1_000_000).quantize(Decimal("0.01")),
        weighted_distribution=(
            None if pd.isna(r.WTD)
            else Decimal(r.WTD).quantize(Decimal("0.01"))
        ),
        period_weeks=4,
    )
    for r in df.itertuples(index=False)
]
Data.objects.bulk_create(rows, ignore_conflicts=True, batch_size=10_000)
```

Rows whose `MARKET_TAG`, `PRODUCT_TAG`, or `PERIOD_TAG` is not present in the corresponding dict are silently dropped. Rows whose `VAL` is `NaN` are silently dropped. Rows whose `WTD` is `NaN` are kept with `weighted_distribution = NULL`.

### Phase 3 — Output

```python
loaded = Data.objects.count() - count_before
self.stdout.write(f"Loaded {loaded} rows from {foldername}.")
```

---

## Field derivations

| Model field | Source | Transformation |
|---|---|---|
| `Brand.description` | `prod.GL Brand` | as-is |
| `SubBrand.description` | `prod.GL Sub Brand` | as-is; `brand` from `GL Brand` |
| `Product.description` | `prod.SDESC` | as-is; `sub_brand` from `(GL Sub Brand, GL Brand)` |
| `Market.description` | `mkt.SHORT` | as-is |
| `Market.description_2` | `mkt.LONG` | as-is |
| `Data.value` | `data.VAL` | `Decimal(VAL * 1_000_000).quantize("0.01")`; row skipped if `VAL` is `NaN` |
| `Data.weighted_distribution` | `data.WTD` | `Decimal(WTD).quantize("0.01")`; `NULL` if `NaN` |
| `Data.date` | `per.DATETIME` (joined via `PERIOD_TAG`) | already a `datetime.date` |
| `Data.period_weeks` | constant | `4` |

`VAL` is described upstream as "scaled in millions of DKK"; multiplying by 1,000,000 stores the raw DKK value in `Data.value`, preserving precision for small rows that would otherwise round to `0.00`.

`period_weeks` is `4` because the `_per` file represents 4-weekly (monthly-ish) reporting periods — `RANK` ranges 1..12 per year and `DATETIME` values are spaced ~28 days apart.

---

## Error handling

| Condition | Behaviour |
|---|---|
| Folder `docs/data/<foldername>/` not found | `CommandError` raised before opening the DB transaction |
| Any of `_data`/`_mkt`/`_per`/`_prod` missing in the folder | `CommandError` before transaction |
| More than one file matches a required suffix | `CommandError` before transaction |
| `_prod` is empty after the `LEAF_LEVEL` filter | `CommandError` (nothing to join data rows against) |
| Data row with `VAL = NaN` | Row silently skipped |
| Data row with `WTD = NaN` | Row kept; `weighted_distribution = NULL` |
| Data row's `MARKET_TAG` / `PRODUCT_TAG` / `PERIOD_TAG` missing from companion file | Row silently skipped |
| Any other exception during phase 1 or phase 2 | Propagates; `transaction.atomic()` rolls back all changes |

All errors are all-or-nothing — no partial imports.

---

## Acceptance criteria

1. `python manage.py load_parquet <foldername>` loads all valid rows from `docs/data/<foldername>/` into the database.
2. Running the command twice on the same folder produces identical row counts in all five tables; the second run reports `Loaded 0 rows`.
3. A shared `GL Brand` value across multiple products results in a single `Brand` row.
4. Only `prod` rows with `LEVEL == LEAF_LEVEL` produce `Product` rows; data rows referencing non-leaf `PRODUCT_TAG` are silently skipped.
5. `Data` rows are unique on `(market, product, date)`, enforced by the new constraint.
6. A row with `VAL = NaN` does not produce a `Data` row.
7. A row with `WTD = NaN` produces a `Data` row with `weighted_distribution = NULL`.
8. `Data.value` stores `VAL × 1,000,000`, quantized to two decimals.
9. `Data.period_weeks == 4` for every row.
10. A missing folder, or a folder missing any of `_data` / `_mkt` / `_per` / `_prod`, raises `CommandError` before any DB write.
11. Any error during processing rolls back all changes (no partial imports).

---

## Tests

**Location:** `backend/market_data/tests/test_load_parquet.py`

A `write_parquet_folder(name, mkt_df, per_df, prod_df, data_df)` fixture writes the four files with the appropriate suffix into a temp folder under `docs/data/` and removes the folder afterward (parallel to `write_csv` in `test_load_csv.py`).

| # | Name | What it verifies |
|---|---|---|
| 1 | Happy path | Tiny fixture (3 mkt, 3 per, 3 leaf prod, 5 data rows). Counts in all five tables; spot-check one `Data` row's `value`, `weighted_distribution`, `date`, `period_weeks`. `Loaded 5 rows from <folder>.` |
| 2 | Idempotency | Run twice; second run prints `Loaded 0 rows`; counts unchanged. |
| 3 | Brand de-dup | Two leaf products sharing `GL Brand` → one `Brand` row, two `Product` rows. |
| 4 | Non-leaf prod filter | Mix of leaf and non-leaf prod rows; data rows reference both. Only leaf products produce `Product` rows; data rows pointing at non-leaf `PRODUCT_TAG` are skipped. |
| 5 | NaN VAL skipped | Row with `VAL = NaN` does not create a `Data` row; sibling rows do. |
| 6 | NaN WTD stored as NULL | Row with `WTD = NaN` creates `Data` row with `weighted_distribution IS NULL`. |
| 7 | VAL scaling | `VAL = 0.0011` → `Data.value == Decimal("1100.00")`. |
| 8 | Dangling TAG silent-skip | Data row references a `MARKET_TAG` / `PRODUCT_TAG` / `PERIOD_TAG` not present in companion files → skipped, no error. |
| 9 | Folder not found | Non-existent foldername → `CommandError`, no DB writes. |
| 10 | Missing required file | Folder exists but `_data` (or `_mkt` / `_per` / `_prod`) missing → `CommandError`, no DB writes. |
| 11 | Unique constraint enforces idempotency | Two data rows with same `(MARKET_TAG, PRODUCT_TAG, PERIOD_TAG)` in input → only one `Data` row created. |
| 12 | Rollback on mid-import error | Monkeypatch `Data.objects.bulk_create` to raise on the second chunk; assert all five tables empty after the error. |
