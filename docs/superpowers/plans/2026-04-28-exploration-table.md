# Exploration Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a server-side sorted, paginated data table with infinite scroll to the `/explore` route, backed by a new DRF endpoint that flattens `Data` and its related models into flat rows.

**Architecture:** A new `DataTableFormatViewSet` in `market_data/views.py` exposes `GET /market-data/table/` via `ReadOnlyModelViewSet` with a custom ordering filter (maps frontend params to ORM traversals) and `PageNumberPagination` (50 rows/page). The frontend replaces the `Explore.tsx` placeholder with an MUI table that fetches on mount, re-fetches on sort changes, and appends rows on infinite scroll via `IntersectionObserver`.

**Tech Stack:** Django REST Framework (`ReadOnlyModelViewSet`, `OrderingFilter`, `PageNumberPagination`, `DefaultRouter`), React 19, MUI v9 (`Table`, `TableSortLabel`), Axios, Jest + React Testing Library.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/market_data/tests/test_views.py` | Create | All backend API tests |
| `backend/market_data/views.py` | Create | Serializer, ordering filter, pagination, viewset |
| `backend/market_data/urls.py` | Create | DRF router wiring for `DataTableFormatViewSet` |
| `backend/redslim/urls.py` | Modify | Include `market_data.urls` under `market-data/` |
| `frontend/src/pages/Explore.test.tsx` | Create | All frontend component tests |
| `frontend/src/pages/Explore.tsx` | Modify | Replace placeholder with full table component |

---

### Task 1: Backend — write all tests (all should fail)

**Files:**
- Create: `backend/market_data/tests/test_views.py`

- [ ] **Step 1: Create the test file**

```python
# backend/market_data/tests/test_views.py
import pytest
from datetime import date
from decimal import Decimal
from rest_framework.test import APIClient
from market_data.models import Brand, SubBrand, Product, Market, Data

TABLE_URL = '/market-data/table/'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def two_records(db):
    brand = Brand.objects.create(description="Brand")
    subbrand = SubBrand.objects.create(description="Sub", brand=brand)
    product = Product.objects.create(description="Product", sub_brand=subbrand)
    market_a = Market.objects.create(description="AAA", description_2="R1")
    market_z = Market.objects.create(description="ZZZ", description_2="R2")
    d1 = Data.objects.create(
        market=market_a, product=product,
        value=Decimal("10.00"), date=date(2022, 1, 1), period_weeks=4,
    )
    d2 = Data.objects.create(
        market=market_z, product=product,
        value=Decimal("20.00"), date=date(2023, 6, 1), period_weeks=4,
    )
    return d1, d2


@pytest.fixture
def fifty_one_records(db):
    brand = Brand.objects.create(description="Brand")
    subbrand = SubBrand.objects.create(description="Sub", brand=brand)
    product = Product.objects.create(description="Product", sub_brand=subbrand)
    market = Market.objects.create(description="Market", description_2="Retailer")
    Data.objects.bulk_create([
        Data(
            market=market, product=product,
            value=Decimal("1.00"),
            date=date(2020, 1, (i % 28) + 1),
            period_weeks=4,
        )
        for i in range(51)
    ])


@pytest.mark.django_db
def test_default_response_has_all_fields_and_date_descending_order(api_client, two_records):
    response = api_client.get(TABLE_URL)
    assert response.status_code == 200
    results = response.data['results']
    assert len(results) == 2
    row = results[0]
    assert set(row.keys()) == {
        'id', 'market', 'product', 'brand', 'sub_brand',
        'value', 'date', 'period_weeks', 'weighted_distribution',
    }
    assert row['market'] == 'ZZZ'
    assert row['product'] == 'Product'
    assert row['brand'] == 'Brand'
    assert row['sub_brand'] == 'Sub'
    assert str(results[0]['date']) == '2023-06-01'
    assert str(results[1]['date']) == '2022-01-01'


@pytest.mark.django_db
def test_ordering_by_market_ascending(api_client, two_records):
    response = api_client.get(TABLE_URL + '?ordering=market')
    results = response.data['results']
    assert results[0]['market'] == 'AAA'
    assert results[1]['market'] == 'ZZZ'


@pytest.mark.django_db
def test_ordering_by_value_descending(api_client, two_records):
    response = api_client.get(TABLE_URL + '?ordering=-value')
    results = response.data['results']
    assert float(results[0]['value']) == 20.00
    assert float(results[1]['value']) == 10.00


@pytest.mark.django_db
def test_pagination_page_size_is_50(api_client, fifty_one_records):
    response = api_client.get(TABLE_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 50


@pytest.mark.django_db
def test_pagination_page_2_and_response_envelope(api_client, fifty_one_records):
    response = api_client.get(TABLE_URL + '?page=2')
    assert response.status_code == 200
    assert len(response.data['results']) == 1
    first_page = api_client.get(TABLE_URL)
    assert first_page.data['count'] == 51
    assert first_page.data['next'] is not None
    assert first_page.data['previous'] is None
```

- [ ] **Step 2: Run tests — verify all 5 fail**

```bash
cd backend && python -m pytest market_data/tests/test_views.py -v
```

Expected: all 5 tests fail (`404` or import errors — neither the viewset nor URLs exist yet). You should see `5 failed`.

---

### Task 2: Backend — viewset + URL wiring

**Files:**
- Create: `backend/market_data/views.py`
- Create: `backend/market_data/urls.py`
- Modify: `backend/redslim/urls.py`

- [ ] **Step 3: Create `backend/market_data/views.py`**

```python
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from market_data.models import Data

_ORDERING_MAP = {
    'market': 'market__description',
    'product': 'product__description',
    'brand': 'product__sub_brand__brand__description',
    'sub_brand': 'product__sub_brand__description',
    'value': 'value',
    'date': 'date',
    'period_weeks': 'period_weeks',
    'weighted_distribution': 'weighted_distribution',
}


class _TableOrderingFilter(OrderingFilter):
    def get_ordering(self, request, queryset, view):
        param = request.query_params.get(self.ordering_param)
        if param:
            fields = []
            for term in param.split(','):
                term = term.strip()
                desc = term.startswith('-')
                orm_field = _ORDERING_MAP.get(term.lstrip('-'))
                if orm_field:
                    fields.append(f'-{orm_field}' if desc else orm_field)
            if fields:
                return fields
        return self.get_default_ordering(view)


class _TablePagination(PageNumberPagination):
    page_size = 50


class DataTableSerializer(serializers.ModelSerializer):
    market = serializers.CharField(source='market.description')
    product = serializers.CharField(source='product.description')
    brand = serializers.CharField(source='product.sub_brand.brand.description')
    sub_brand = serializers.CharField(source='product.sub_brand.description')

    class Meta:
        model = Data
        fields = [
            'id', 'market', 'product', 'brand', 'sub_brand',
            'value', 'date', 'period_weeks', 'weighted_distribution',
        ]


class DataTableFormatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Data.objects.select_related(
        'market', 'product__sub_brand__brand'
    ).order_by('-date')
    serializer_class = DataTableSerializer
    pagination_class = _TablePagination
    filter_backends = [_TableOrderingFilter]
    ordering = ['-date']
```

- [ ] **Step 4: Create `backend/market_data/urls.py`**

```python
from rest_framework.routers import DefaultRouter
from .views import DataTableFormatViewSet

router = DefaultRouter()
router.register('table', DataTableFormatViewSet, basename='data-table')

urlpatterns = router.urls
```

- [ ] **Step 5: Update `backend/redslim/urls.py`**

Replace the entire file with:

```python
from django.urls import path, include

urlpatterns = [
    path('', include('hello.urls')),
    path('market-data/', include('market_data.urls')),
]
```

- [ ] **Step 6: Run the new tests — verify all 5 pass**

```bash
cd backend && python -m pytest market_data/tests/test_views.py -v
```

Expected: `5 passed`.

- [ ] **Step 7: Verify existing tests still pass**

```bash
cd backend && python -m pytest -v
```

Expected: all tests pass, `0 failed`.

- [ ] **Step 8: Commit**

```bash
git add backend/market_data/views.py backend/market_data/urls.py backend/redslim/urls.py backend/market_data/tests/test_views.py
git commit -m "feat: add DataTableFormatViewSet with sorting and pagination"
```

---

### Task 3: Frontend — write all tests (all should fail)

**Files:**
- Create: `frontend/src/pages/Explore.test.tsx`

- [ ] **Step 9: Create the test file**

```tsx
// frontend/src/pages/Explore.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Explore from './Explore'
import apiClient from '../api/client'

jest.mock('../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}))

const mockRow = {
  id: 1,
  market: 'MarketA',
  product: 'ProductA',
  brand: 'BrandA',
  sub_brand: 'SubBrandA',
  value: '100.00',
  date: '2023-01-15',
  period_weeks: 4,
  weighted_distribution: '50.00',
}

const mockPage = {
  data: { count: 1, next: null, previous: null, results: [mockRow] },
}

beforeEach(() => {
  jest.mocked(apiClient.get).mockReset()
  global.IntersectionObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    disconnect: jest.fn(),
    unobserve: jest.fn(),
  }))
})

test('renders all 8 column headers', async () => {
  jest.mocked(apiClient.get).mockResolvedValue(mockPage)
  render(<Explore />)
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1))
  expect(screen.getByText('Market')).toBeInTheDocument()
  expect(screen.getByText('Product')).toBeInTheDocument()
  expect(screen.getByText('Brand')).toBeInTheDocument()
  expect(screen.getByText('Sub-Brand')).toBeInTheDocument()
  expect(screen.getByText('Sales Value')).toBeInTheDocument()
  expect(screen.getByText('Date')).toBeInTheDocument()
  expect(screen.getByText('Period (Weeks)')).toBeInTheDocument()
  expect(screen.getByText('Weighted Distribution')).toBeInTheDocument()
})

test('clicking inactive column fires request with correct ordering param', async () => {
  jest.mocked(apiClient.get).mockResolvedValue(mockPage)
  render(<Explore />)
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1))
  await userEvent.click(screen.getByText('Market'))
  await waitFor(() => {
    expect(apiClient.get).toHaveBeenCalledTimes(2)
    const lastUrl = jest.mocked(apiClient.get).mock.calls[1][0] as string
    expect(lastUrl).toContain('ordering=market')
    expect(lastUrl).not.toContain('ordering=-market')
  })
})

test('clicking active column header toggles sort direction', async () => {
  jest.mocked(apiClient.get).mockResolvedValue(mockPage)
  render(<Explore />)
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1))
  // Default active sort is date desc. Clicking Date toggles to asc (no leading minus).
  await userEvent.click(screen.getByText('Date'))
  await waitFor(() => {
    expect(apiClient.get).toHaveBeenCalledTimes(2)
    const lastUrl = jest.mocked(apiClient.get).mock.calls[1][0] as string
    expect(lastUrl).toContain('ordering=date')
    expect(lastUrl).not.toContain('ordering=-date')
  })
})

test('shows CircularProgress during initial fetch', async () => {
  jest.mocked(apiClient.get).mockReturnValue(new Promise(() => {}))
  render(<Explore />)
  await waitFor(() => {
    expect(document.querySelector('[role="progressbar"]')).toBeInTheDocument()
  })
})

test('shows No data available when API returns empty list', async () => {
  jest.mocked(apiClient.get).mockResolvedValue({
    data: { count: 0, next: null, previous: null, results: [] },
  })
  render(<Explore />)
  await waitFor(() => {
    expect(screen.getByText('No data available')).toBeInTheDocument()
  })
})
```

- [ ] **Step 10: Run tests — verify all 5 fail**

```bash
cd frontend && npx jest src/pages/Explore.test.tsx --no-coverage
```

Expected: all 5 tests fail (current `Explore.tsx` is a placeholder with no table, no fetch, no sorting). You should see `5 failed`.

---

### Task 4: Frontend — Explore.tsx full implementation

**Files:**
- Modify: `frontend/src/pages/Explore.tsx`

- [ ] **Step 11: Replace `frontend/src/pages/Explore.tsx` with the full implementation**

```tsx
import { useState, useEffect, useRef } from 'react'
import {
  Box,
  CircularProgress,
  Container,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Typography,
} from '@mui/material'
import apiClient from '../api/client'

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

type SortOrder = 'asc' | 'desc'

const COLUMNS: { key: string; label: string }[] = [
  { key: 'market', label: 'Market' },
  { key: 'product', label: 'Product' },
  { key: 'brand', label: 'Brand' },
  { key: 'sub_brand', label: 'Sub-Brand' },
  { key: 'value', label: 'Sales Value' },
  { key: 'date', label: 'Date' },
  { key: 'period_weeks', label: 'Period (Weeks)' },
  { key: 'weighted_distribution', label: 'Weighted Distribution' },
]

function Explore() {
  const [rows, setRows] = useState<DataRow[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [sortField, setSortField] = useState('date')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const sentinelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    const ordering = `${sortOrder === 'desc' ? '-' : ''}${sortField}`
    setLoading(true)
    apiClient
      .get(`/market-data/table/?page=${page}&ordering=${ordering}`)
      .then(({ data }) => {
        if (!cancelled) {
          setRows((prev) => (page === 1 ? data.results : [...prev, ...data.results]))
          setHasMore(data.next !== null)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, sortField, sortOrder])

  const handleSort = (field: string) => {
    if (field === sortField) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
    setRows([])
    setPage(1)
  }

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !loading && hasMore) {
        setPage((prev) => prev + 1)
      }
    })
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [loading, hasMore])

  return (
    <Container maxWidth="xl" className="py-8">
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              {COLUMNS.map(({ key, label }) => (
                <TableCell key={key}>
                  <TableSortLabel
                    active={sortField === key}
                    direction={sortField === key ? sortOrder : 'asc'}
                    onClick={() => handleSort(key)}
                  >
                    {label}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.market}</TableCell>
                <TableCell>{row.product}</TableCell>
                <TableCell>{row.brand}</TableCell>
                <TableCell>{row.sub_brand}</TableCell>
                <TableCell>{row.value}</TableCell>
                <TableCell>{row.date}</TableCell>
                <TableCell>{row.period_weeks}</TableCell>
                <TableCell>{row.weighted_distribution ?? '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <div ref={sentinelRef} />
      {loading && (
        <Box className="flex justify-center py-4">
          <CircularProgress />
        </Box>
      )}
      {!loading && rows.length === 0 && (
        <Box className="flex justify-center py-4">
          <Typography>No data available</Typography>
        </Box>
      )}
    </Container>
  )
}

export default Explore
```

- [ ] **Step 12: Run the new tests — verify all 5 pass**

```bash
cd frontend && npx jest src/pages/Explore.test.tsx --no-coverage
```

Expected: `5 passed`.

- [ ] **Step 13: Verify existing frontend tests still pass**

```bash
cd frontend && npm test -- --no-coverage
```

Expected: all tests pass, `0 failed`.

- [ ] **Step 14: Commit**

```bash
git add frontend/src/pages/Explore.tsx frontend/src/pages/Explore.test.tsx
git commit -m "feat: add exploration table with infinite scroll and sort"
```
