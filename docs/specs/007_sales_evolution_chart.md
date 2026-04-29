# Spec 007 - Sales Evolution Chart

**Date:** 2026-04-29
**Source spec:** `docs/specs/007_sales_evolution_chart.md`

## Overview

A new `/evolution` page that renders a bar chart showing accumulated sales value over calendar years for a user-selected category member (Brand, Product, or Market). Two cascading selectors drive the chart; the chart area shows a prompt until both selectors are set.

---

## Backend

### New endpoints

Both are `APIView` classes added to `market_data/views.py` and registered under the existing `/market-data/` URL prefix.

#### `EvolutionOptionsView`
```
GET /market-data/evolution/options/?category=<brand|product|market>&page=<N>
```

Returns a sorted, paginated list of distinct, non-empty string values for the requested category. Pagination uses the existing `_TablePagination` (DRF `PageNumberPagination`, `page_size = 50`); the response follows the standard DRF envelope so the frontend can drive load-more off `next`.

Category → ORM field mapping:
- `brand` → `product__sub_brand__brand__description`
- `product` → `product__description`
- `market` → `market__description`

Rows where the resolved field is null or empty string are excluded. Returns `400` for unknown category values.

**Response shape:**
```json
{
  "count": 137,
  "next": "http://.../market-data/evolution/options/?category=brand&page=2",
  "previous": null,
  "results": ["Brand A", "Brand B", "Brand C"]
}
```

#### `EvolutionChartView`
```
GET /market-data/evolution/chart/?category=<brand|product|market>&value=<string>
```

Filters `Data` rows to those matching `value` for the given category (same null/empty exclusion), groups by `date__year`, sums `value`, and returns results sorted ascending by year. Returns `400` if `category` is unknown or `value` is missing.

**Response shape:**
```json
[
  { "year": 2020, "total": "12345.67" },
  { "year": 2021, "total": "98765.43" }
]
```

---

## Frontend

### New route and nav link

- Route: `/evolution` → `Evolution.tsx` added to `App.tsx`
- Nav link `"Evolution"` added to `Layout.tsx` following the existing active-state pattern

### `Evolution.tsx` — page component

**State:**

| Variable | Type | Purpose |
|---|---|---|
| `category` | `'brand' \| 'product' \| 'market' \| ''` | Selector 1 value |
| `options` | `string[]` | Selector 2 option list, accumulated page-by-page |
| `optionsPage` | `number` | Last options page loaded; starts at 0 |
| `optionsHasMore` | `boolean` | True while the last response had a non-null `next` |
| `selectedValue` | `string` | Selector 2 value |
| `chartData` | `{ year: number; total: number }[]` | Aggregated chart data |
| `loadingOptions` | `boolean` | Options fetch in-flight (initial OR subsequent page) |
| `loadingChart` | `boolean` | Chart data fetch in-flight |

**Behavior:**

- Selector 2 is disabled while `category` is unset OR while the first page is loading and no options have been received yet.
- When `category` changes: clear `selectedValue`, `chartData`, `options`; reset `optionsPage = 0`, `optionsHasMore = true`; fetch page 1.
- When the open dropdown is scrolled near its bottom and `optionsHasMore`, fetch the next page and append to `options`.
- A non-selectable spinner row is rendered at the end of the list while a subsequent page is loading.
- When both selectors are set: fetch chart data.
- Chart area shows a placeholder message until both selectors are set.
- On data load: render chart.

**Chart area states:**

1. Either selector unset → placeholder: *"Select a category and a value to see the evolution chart."*
2. Options loading → `CircularProgress` in selector 2
3. Both set, chart loading → `CircularProgress` in chart area
4. Data loaded, no rows → `"No data available"`
5. Data loaded, rows present → `BarChart`

**Chart:** Recharts `BarChart` inside `ResponsiveContainer` + `Paper`, following the same pattern as `Dominance.tsx`:
- `XAxis` dataKey `year`
- `YAxis` formatted as currency (no decimals), using the unit defined for `Data.value` in spec 002 (DKK)
- `Bar` dataKey `total`
- `CartesianGrid` (dashed)
- `Tooltip` formatted as currency, using the unit defined for `Data.value` in spec 002 (DKK)

---

## Data flow

```
User picks category (selector 1)
  → clear selectedValue, chartData, options
  → reset optionsPage=0, optionsHasMore=true
  → GET /market-data/evolution/options/?category=<category>&page=1
  → populate selector 2 options; set optionsHasMore from `next`

User scrolls selector 2 dropdown near its bottom (and optionsHasMore)
  → GET /market-data/evolution/options/?category=<category>&page=<optionsPage+1>
  → append results to options; update optionsHasMore from `next`

User picks value (selector 2)
  → GET /market-data/evolution/chart/?category=<category>&value=<value>
  → render BarChart

User changes category (selector 1 again)
  → repeat from top
```

---

## Error handling

Both fetch calls use silent catch (same pattern as `Dominance.tsx`): on failure, loading state resets and the UI remains in an empty but non-broken state. No error toast or retry mechanism.

Backend returns `400` for unknown `category` query param values; the frontend treats this as a failed fetch.

---

## Testing

**Backend (pytest):**
- `EvolutionOptionsView`: valid categories return paginated, sorted lists; unknown category returns 400; null/empty values excluded.
- `EvolutionOptionsView` pagination: first page returns up to 50 items with non-null `next` when more exist; second page returns the remaining items with `next` null and `previous` non-null.
- `EvolutionChartView`: correct year aggregation; null/empty exclusion; results sorted by year ascending.

**Frontend (Jest):**
- Initial render: both selectors shown, chart area shows placeholder, selector 2 disabled.
- After category select: first page of options loaded, selector 2 enabled.
- Scrolling near the bottom of the open dropdown triggers a page-2 fetch; appended options appear in the list.
- When the response indicates no `next`, further scroll events do not fire additional requests.
- After value select: chart renders with correct data.
- Category change after chart render: selector 2 resets, chart clears, page state resets.
