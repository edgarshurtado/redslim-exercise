# Spec 006 - Manufacturer Dominance Treemap — Design Spec

**Date:** 2026-04-28

---

## Overview

A new page at `/dominance` that renders a treemap of brands, where:

- **Box size** = total accumulated sales value (`SUM(value)`) per brand
- **Box color** = sales-weighted average weighted distribution (`SUM(value × wtd) / SUM(value)`) per brand, mapped on a green → red scale

The goal is to surface "efficient" brands (high sales, lean distribution) vs "bloated" brands (high distribution, lower relative sales). Data is aggregated across all markets and all periods — no filters.

---

## Data & API

### Endpoint

`GET /market-data/dominance/`

Returns a flat JSON array — no pagination. Brand count is small enough to return in one shot.

### Aggregation logic

Computed from the `Data` model, grouped by brand (`product__sub_brand__brand`). **Rows whose brand description is an empty string are excluded before aggregation.**

| Field | Formula |
|---|---|
| `total_value` | `SUM(value)` across all rows for the brand |
| `weighted_avg_wtd` | `SUM(value × weighted_distribution) / SUM(value)` for rows where `weighted_distribution IS NOT NULL` |

If every row for a brand has a null `weighted_distribution`, `weighted_avg_wtd` is returned as `null`.

### Response shape

```json
[
  { "brand": "UT PLUS", "total_value": "4200000.00", "weighted_avg_wtd": "38.20" },
  { "brand": "PRIVATE LABEL", "total_value": "850000.00", "weighted_avg_wtd": null }
]
```

### Implementation

- New `BrandDominanceView` (`APIView`) in `backend/market_data/views.py`
- Two-pass ORM annotation: first annotate `wtd_numerator` and `wtd_denominator`, then divide in Python within the view
- New URL entry: `path('dominance/', BrandDominanceView.as_view())` appended to `urlpatterns` in `backend/market_data/urls.py` (already mounted under `market-data/` in the root router, so the full path becomes `market-data/dominance/`)

---

## Frontend

### Routing & navigation

- `App.tsx`: add `<Route path="/dominance" element={<Dominance />} />`
- `Layout.tsx`: add a "Dominance" nav link using the same active-underline pattern as "Explore"

### `pages/Dominance.tsx` (new file)

**Data fetching:**
- Single `GET /market-data/dominance/` on mount via the existing `apiClient`
- No pagination, no sorting controls

**Treemap rendering:**
- Library: `recharts` (to be installed)
- Component: `<Treemap dataKey="total_value" />` wrapped in `<ResponsiveContainer width="100%" height={500} />` so it fills the container width and has a fixed 500px height
- Custom `content` prop renders each cell:
  - Brand label (omitted when box is too small to fit text)
  - WTD % label below the brand name

**Color encoding:**
- Compute `min` and `max` of `weighted_avg_wtd` across the returned dataset
- Normalize each brand's WTD to `[0, 1]` within that range
- Linearly interpolate between `#2e7d32` (green, efficient) and `#c62828` (red, bloated)
- Brands with `weighted_avg_wtd = null` render in neutral grey `#9e9e9e`

**Color legend:**
- Displayed above the treemap: `Efficient ── [green→red gradient bar] ── Bloated`
- One-line subtitle below the page title explains the encoding:
  > "Box size = total sales value · Box color = sales-weighted distribution (green = lean, red = bloated)"

**Tooltip:**
- Recharts `<Tooltip>` with a custom `content` prop
- Shows on hover: brand name, formatted total sales value, WTD %
- Sales value is formatted as currency using the unit defined for `Data.value` in spec 002 (DKK)

**States:**
- Loading: centered `<CircularProgress />` (same pattern as Explore)
- Empty / error: centered `<Typography>No data available</Typography>`

---

## Error Handling

| Condition | Behaviour |
|---|---|
| API fetch failure | Show "No data available" message |
| Brand with all-null WTD | Rendered in neutral grey; no error |
| No brands returned | Show "No data available" message |

No retry logic — user reloads the page.

---

## Testing

### Backend (`pytest`)

| # | What it verifies |
|---|---|
| 1 | Happy path: known fixture data returns correct `total_value` and `weighted_avg_wtd` (verify the weighted math explicitly) |
| 2 | Null WTD handling: brand with all-null WTD rows returns `weighted_avg_wtd: null` |
| 3 | Mixed null/non-null WTD: only non-null rows contribute to the weighted average |
| 4 | Empty brand exclusion: rows whose brand description is `""` are not included in the response |

### Frontend (`jest` + Testing Library)

| # | What it verifies |
|---|---|
| 1 | Page renders brand names from mocked API response |
| 2 | Loading spinner shown while fetch is in flight |
| 3 | "No data available" shown when API returns empty array |

---

## File Checklist

| File | Change |
|---|---|
| `backend/market_data/views.py` | Add `BrandDominanceView` |
| `backend/market_data/urls.py` | Add `dominance/` route |
| `backend/market_data/tests/test_dominance.py` | New test file |
| `frontend/src/App.tsx` | Add `/dominance` route |
| `frontend/src/components/Layout.tsx` | Add Dominance nav link |
| `frontend/src/pages/Dominance.tsx` | New page component |
| `frontend/package.json` | Add `recharts` dependency |
