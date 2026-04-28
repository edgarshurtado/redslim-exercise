# Spec 005 — Exploration Table Design

**Date:** 2026-04-28
**Branch:** exploration_table

## Overview

Add a sortable, paginated data table to the `/explore` route. The table surfaces rows from the `Data` model with columns flattened across the `Market`, `Product`, `SubBrand`, and `Brand` models. Sorting and pagination are server-side. Infinite scroll triggers next-page fetches as the user scrolls to the bottom.

---

## Backend

### `DataTableFormatViewSet`

**Location:** `backend/market_data/views.py` (new file)

Extends DRF `ReadOnlyModelViewSet`. Queryset uses `select_related('market', 'product__sub_brand__brand')` to avoid N+1 queries.

**Serializer** (`DataTableSerializer`) flattens the join into a single row:

```
{ id, market, product, brand, sub_brand, value, date, period_weeks, weighted_distribution }
```

Field sources:

| Serializer field | Model source |
|---|---|
| `market` | `market.description` |
| `product` | `product.description` |
| `brand` | `product.sub_brand.brand.description` |
| `sub_brand` | `product.sub_brand.description` |
| `value` | `value` |
| `date` | `date` |
| `period_weeks` | `period_weeks` |
| `weighted_distribution` | `weighted_distribution` (nullable) |

**Sorting** via DRF `OrderingFilter`. Allowed ordering fields map frontend params to ORM traversals:

| `ordering` param | ORM field |
|---|---|
| `market` | `market__description` |
| `product` | `product__description` |
| `brand` | `product__sub_brand__brand__description` |
| `sub_brand` | `product__sub_brand__description` |
| `value` | `value` |
| `date` | `date` |
| `period_weeks` | `period_weeks` |
| `weighted_distribution` | `weighted_distribution` |

**Pagination** via DRF `PageNumberPagination`, page size 50. Default ordering: `-date` (most recent first).

**Response shape:**

```json
{
  "count": 1500,
  "next": "http://localhost:8000/market-data/table/?page=2",
  "previous": null,
  "results": [{ "id": 1, "market": "...", ... }]
}
```

### URL wiring

New `backend/market_data/urls.py` registers the viewset with a DRF `DefaultRouter` at prefix `table`. Included in `backend/redslim/urls.py` under `market-data/`.

Full endpoint: `GET /market-data/table/?page=1&ordering=-date`

---

## Frontend

### `Explore.tsx`

Replaces the current placeholder at `frontend/src/pages/Explore.tsx`.

**State:**

| Variable | Type | Initial value | Purpose |
|---|---|---|---|
| `rows` | `DataRow[]` | `[]` | Accumulated rows across all fetched pages |
| `page` | `number` | `1` | Next page to request |
| `hasMore` | `boolean` | `true` | Whether the API has more pages |
| `loading` | `boolean` | `false` | Fetch in-flight flag |
| `sortField` | `string` | `'date'` | Active sort column |
| `sortOrder` | `'asc' \| 'desc'` | `'desc'` | Active sort direction |

**Sort interaction:** Clicking an inactive column header sets it as active with `'asc'`. Clicking the active header toggles direction. On any sort change: clear `rows`, reset `page` to `1`, and re-fetch.

**API call:**
```
GET /market-data/table/?page={page}&ordering={sortOrder === 'desc' ? '-' : ''}{sortField}
```

**TypeScript type:**

```ts
interface DataRow {
  id: number
  market: string
  product: string
  brand: string
  sub_brand: string
  value: string
  date: string
  period_weeks: number
  weighted_distribution: string | null
}
```

### Infinite scroll

An invisible `<div ref={sentinelRef} />` is placed **below** `TableContainer` (outside the table element — a `<div>` inside `<tbody>` is invalid HTML). A single `IntersectionObserver` watches it — when it enters the viewport and `!loading && hasMore`, increment `page` (which triggers a `useEffect` fetch) and append new rows to `rows`.

### Table structure

MUI components: `TableContainer` → `Table` → `TableHead` / `TableBody`. Each of the 8 header cells uses `TableSortLabel` with `active` and `direction` props driven by state. Column order matches the spec:

1. Market
2. Product
3. Brand
4. Sub-Brand
5. Sales Value
6. Date
7. Period (Weeks)
8. Weighted Distribution

### Loading & empty states

- `CircularProgress` centered below the last row while `loading` is true.
- `Typography` "No data available" when `rows` is empty and `loading` is false.

---

## Testing

### Backend (`backend/market_data/tests/test_views.py`)

- Default response returns rows ordered by `-date` with all expected fields present
- `?ordering=market` sorts by `market__description` ascending
- `?ordering=-value` sorts by value descending
- Pagination: page size is 50; `?page=2` returns second batch; response includes `count`, `next`, `previous`

### Frontend (`frontend/src/pages/Explore.test.tsx`)

- Renders all 8 column headers with mocked axios data
- Clicking an inactive column header fires a request with the correct `ordering` param
- Clicking the active column header toggles between `asc` and `desc`
- `CircularProgress` is present while the initial fetch is in-flight
- "No data available" appears when the API returns an empty list

---

## Out of scope

- Filtering / search
- Column visibility toggles
- CSV/export functionality
- Mobile-responsive table layout
