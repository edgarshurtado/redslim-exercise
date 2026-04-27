# Spec 002 — Database Schema

Define the PostgreSQL schema to store retail sales data. Five entities: `Market`, `Brand`, `SubBrand`, `Product`, and `Data`. The brand hierarchy (`Brand → SubBrand → Product`) is fully normalized. `Data` is the fact table linking a product and a market to a sales measurement at a point in time.

---

## Entity Relationship Diagram

```mermaid
erDiagram
    Brand {
        int id PK
        string description
    }
    SubBrand {
        int id PK
        string description
        int brand_fk FK
    }
    Product {
        int id PK
        string description
        int sub_brand_fk FK
    }
    Market {
        int id PK
        string description
        string description_2
    }
    Data {
        int id PK
        int market_fk FK
        int product_fk FK
        int value
        int weighted_distribution
        date date
        int period_weeks
    }

    Brand ||--o{ SubBrand : "has"
    SubBrand ||--o{ Product : "has"
    Market ||--o{ Data : "measured in"
    Product ||--o{ Data : "appears in"
```

---

## Entities

### Brand

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | int (PK) | No | Auto-generated primary key |
| `description` | string | No | Brand name |

---

### SubBrand

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | int (PK) | No | Auto-generated primary key |
| `description` | string | No | Sub-brand name |
| `brand_fk` | int (FK → Brand) | No | Parent brand — CASCADE on delete |

---

### Product

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | int (PK) | No | Auto-generated primary key |
| `description` | string | No | Full product description |
| `sub_brand_fk` | int (FK → SubBrand) | No | Parent sub-brand — CASCADE on delete |

---

### Market

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | int (PK) | No | Auto-generated primary key |
| `description` | string | No | Primary market identifier (e.g. `"MARKET3"`) |
| `description_2` | string | No | Secondary market / retailer description (e.g. `"TOT RETAILER 1"`) |

---

### Data

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | int (PK) | No | Auto-generated primary key |
| `market_fk` | int (FK → Market) | No | Market where the measurement was taken — CASCADE on delete |
| `product_fk` | int (FK → Product) | No | Product being measured — CASCADE on delete |
| `value` | int | No | Sales value for the period |
| `weighted_distribution` | int | No | Distribution reach × 100 (e.g. `9400` = 94%) |
| `date` | date | No | End date of the reporting period |
| `period_weeks` | int | No | Duration of the reporting period in weeks |

---

## Acceptance Criteria

1. All five tables exist in the PostgreSQL database: `brand`, `subbrand`, `product`, `market`, `data`.
2. All foreign keys use `ON DELETE CASCADE`: deleting a `Brand` cascades to its `SubBrand` rows, then to `Product`, then to `Data`; deleting a `Market` cascades to its `Data` rows.
3. No nullable fields — all columns have `NOT NULL` constraints.
4. `Data.weighted_distribution` stores values multiplied by 100 (e.g. `9400` for 94%) — no decimal columns.
5. Django migrations apply cleanly against the PostgreSQL instance defined in spec 001 (`redslim-exercise` DB, `redslim` user).
