# Evolution Options — Paginated Loading (design)

**Date:** 2026-04-29
**Related spec:** `docs/specs/007_sales_evolution_chart.md`

## Problem

Spec 007 defines a second selector that lists every distinct value for the chosen category (Brand, Product, or Market). For categories with many distinct values (potentially thousands), returning the full list in a single response is wasteful and the dropdown becomes unwieldy.

## Decision

Paginate the second selector with **infinite scroll inside the dropdown**. No search input. The first page loads eagerly when the user picks a category; subsequent pages load when the user scrolls near the bottom of the open dropdown.

## Why these choices

**Infinite scroll over search-as-you-type or hybrid.** Users will primarily browse the list, not search it; adding an input box contradicts that intent. Infinite scroll keeps the existing UX shape (a simple `Select`) and adds only the load-more behavior.

**DRF `PageNumberPagination` reusing the existing `_TablePagination` style.** The codebase already paginates the Explore table this way (`page_size = 50`, response envelope `{count, next, previous, results}`). Reusing that pattern keeps the backend coherent and lets the frontend drive load-more off `next` being non-null.

**Keep MUI `Select`, do not switch to `Autocomplete`.** `Autocomplete` is the more idiomatic MUI component for paged option lists, but it adds a text input at the top of the dropdown by default. Since we explicitly chose "browse, not search," the input would be a UX contradiction. `Select` with a scroll listener on the dropdown's paper does the job with a smaller diff.

**Eager first-page fetch on category change.** Matches current behavior, makes the dropdown feel instant. The 50-row request is small enough that lazy loading on dropdown-open isn't worth the perceived delay.

## Backend

`EvolutionOptionsView` (in `backend/market_data/views.py`) becomes paginated:

- Response shape changes from `["A", "B", "C"]` to `{"count": N, "next": "...?page=2", "previous": null, "results": ["A", "B", ...]}`.
- Pagination uses `_TablePagination` (page_size 50). The view either reuses that class directly or refactors to a `GenericAPIView` with `pagination_class` set; the manual `paginate_queryset` / `get_paginated_response` path keeps the view shape closest to today.
- Distinct/sort/null-empty exclusion semantics unchanged.
- `400` on unknown category unchanged.

`EvolutionChartView` is **not** modified. The chart endpoint already returns one row per year, which is small.

## Frontend

`Evolution.tsx` state:

| Variable | Type | Purpose |
|---|---|---|
| `category` | `'brand' \| 'product' \| 'market' \| ''` | Selector 1 value (unchanged) |
| `options` | `string[]` | Accumulated list across pages |
| `optionsPage` | `number` | Last page loaded; starts at 0 |
| `optionsHasMore` | `boolean` | True while the last response had a non-null `next` |
| `selectedValue` | `string` | Selector 2 value (unchanged) |
| `chartData` | `{ year, total }[]` | Chart data (unchanged) |
| `loadingOptions` | `boolean` | Covers both initial and subsequent page loads |
| `loadingChart` | `boolean` | Unchanged |

Flow:

1. **Category change** — clear `options`, `selectedValue`, `chartData`; reset `optionsPage = 0`, `optionsHasMore = true`. Fetch page 1 eagerly.
2. **First page response** — set `options = results`, `optionsPage = 1`, `optionsHasMore = next !== null`.
3. **Scroll near bottom** of open dropdown — if `optionsHasMore && !loadingOptions`, fetch `page = optionsPage + 1`; append `results` to `options`, increment `optionsPage`, update `optionsHasMore` from `next`.
4. **Cancellation** — extend the existing `cancelled` flag pattern so a category change mid-fetch doesn't pollute the new category's options.
5. **Errors** — silent catch; loading state resets, UI remains in a non-broken empty state. No toast or retry. (Same as today.)

UI mechanics:

- Trigger via `MenuProps.slotProps.paper.onScroll`, firing the next-page fetch when `scrollTop + clientHeight >= scrollHeight - 50`.
- While `loadingOptions && options.length > 0`, render a non-selectable `MenuItem` at the end of the list with a small `CircularProgress`.
- Initial load (when `options.length === 0`) keeps the existing disabled-selector + spinner-in-control behavior.

## Testing

**Backend (pytest):**
- Response uses the DRF paginated envelope (`count`, `next`, `previous`, `results`).
- First page returns up to 50 results; `next` is non-null when more exist, null on the last page.
- `?page=2` returns the next slice with sorting consistent across pages.
- Existing assertions update from `response.data == [...]` to `response.data['results'] == [...]`.
- Unchanged: 400 on unknown category, null/empty-string exclusion.

**Frontend (Jest):**
- Initial render: placeholder shown, selector 2 disabled (unchanged).
- After category select: first page of options loaded; selector 2 enabled.
- Scrolling near the bottom of the open dropdown triggers a page-2 fetch; new options appear appended.
- When the response has no `next`, further scroll events don't fire additional requests.
- Category change while options are mid-fetch: in-flight request is cancelled, new options replace old, page state resets.

## Updates to spec 007

Spec 007 is amended in place rather than superseded:

- `EvolutionOptionsView` response shape switches to the paginated envelope; add a line referencing `_TablePagination` and `?page=N`.
- Frontend state table gains `optionsPage` and `optionsHasMore`; note that `loadingOptions` now covers subsequent page loads too.
- Behavior bullets gain the scroll-triggered next-page fetch.
- Data-flow diagram adds the load-more branch.
- Testing section gains the pagination cases above.

## Out of scope

- Search/filter inside the dropdown.
- Virtualized list rendering. The accumulated `options` array stays in memory; if a category ever has tens of thousands of distinct values, revisit with virtualization or by introducing search.
- Pagination of `EvolutionChartView`.
- Persisting the selected value across reloads (the current spec does not, and this change does not introduce it).
