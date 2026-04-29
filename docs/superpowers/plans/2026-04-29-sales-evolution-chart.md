# Sales Evolution Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/evolution` page with cascading selectors and a Recharts bar chart that shows accumulated annual sales value for a user-selected Brand, Product, or Market.

**Architecture:** Two new Django `APIView` classes handle option-list and chart-data queries; a new React page component drives cascading selector state, fetches from both endpoints, and renders the chart only once both selectors are set.

**Tech Stack:** Django REST Framework, Django ORM (`ExtractYear`, `Sum`), React, MUI v9, Recharts v3, pytest, Jest + @testing-library

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `backend/market_data/tests/test_evolution.py` | pytest tests for both new views |
| Modify | `backend/market_data/views.py` | Add `EvolutionOptionsView`, `EvolutionChartView`, `_EVOLUTION_FIELD_MAP` |
| Modify | `backend/market_data/urls.py` | Register two new URL paths |
| Create | `frontend/src/pages/Evolution.tsx` | Page component — selectors + chart |
| Create | `frontend/src/pages/Evolution.test.tsx` | Jest tests for Evolution page |
| Modify | `frontend/src/App.tsx` | Add `/evolution` route |
| Modify | `frontend/src/components/Layout.tsx` | Add Evolution nav link |
| Modify | `frontend/src/components/Layout.test.tsx` | Test evolution nav link active state |

---

## Task 1: EvolutionOptionsView — tests + implementation

**Files:**
- Create: `backend/market_data/tests/test_evolution.py`
- Modify: `backend/market_data/views.py`
- Modify: `backend/market_data/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/market_data/tests/test_evolution.py`:

```python
import datetime
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from market_data.models import Brand, SubBrand, Product, Market, Data


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def market(db):
    return Market.objects.create(description='MARKET1', description_2='TOT RETAILER 1')


def _make_brand_data(brand_name, market_obj, year=2020):
    brand, _ = Brand.objects.get_or_create(description=brand_name)
    sub, _ = SubBrand.objects.get_or_create(description=f'SUB_{brand_name}', brand=brand)
    product, _ = Product.objects.get_or_create(description=f'PROD_{brand_name}', sub_brand=sub)
    Data.objects.create(
        market=market_obj,
        product=product,
        value=Decimal('1000'),
        date=datetime.date(year, 1, 1),
        period_weeks=4,
    )


@pytest.mark.django_db
def test_options_brand_returns_sorted_list(api_client, market):
    _make_brand_data('ZEBRA', market)
    _make_brand_data('ALPHA', market)

    response = api_client.get('/market-data/evolution/options/?category=brand')

    assert response.status_code == 200
    assert response.json() == ['ALPHA', 'ZEBRA']


@pytest.mark.django_db
def test_options_product_returns_sorted_list(api_client, market):
    brand, _ = Brand.objects.get_or_create(description='BRD')
    for prod_name in ['PROD Z', 'PROD A']:
        sub, _ = SubBrand.objects.get_or_create(description=prod_name, brand=brand)
        product, _ = Product.objects.get_or_create(description=prod_name, sub_brand=sub)
        Data.objects.create(
            market=market, product=product, value=Decimal('100'),
            date=datetime.date(2020, 1, 1), period_weeks=4,
        )

    response = api_client.get('/market-data/evolution/options/?category=product')

    assert response.status_code == 200
    assert response.json() == ['PROD A', 'PROD Z']


@pytest.mark.django_db
def test_options_market_returns_sorted_list(api_client, db):
    brand, _ = Brand.objects.get_or_create(description='BRD')
    sub, _ = SubBrand.objects.get_or_create(description='SUB', brand=brand)
    product, _ = Product.objects.get_or_create(description='PROD', sub_brand=sub)
    for mkt_name in ['MARKET B', 'MARKET A']:
        m = Market.objects.create(description=mkt_name, description_2='')
        Data.objects.create(
            market=m, product=product, value=Decimal('100'),
            date=datetime.date(2020, 1, 1), period_weeks=4,
        )

    response = api_client.get('/market-data/evolution/options/?category=market')

    assert response.status_code == 200
    assert response.json() == ['MARKET A', 'MARKET B']


@pytest.mark.django_db
def test_options_unknown_category_returns_400(api_client):
    response = api_client.get('/market-data/evolution/options/?category=invalid')
    assert response.status_code == 400


@pytest.mark.django_db
def test_options_brand_excludes_empty_description(api_client, market):
    _make_brand_data('REAL BRAND', market)
    _make_brand_data('', market)

    response = api_client.get('/market-data/evolution/options/?category=brand')

    assert response.status_code == 200
    assert response.json() == ['REAL BRAND']
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest market_data/tests/test_evolution.py -v -k "options"
```

Expected: 5 failures — 404 Not Found (URL not wired yet).

- [ ] **Step 3: Implement EvolutionOptionsView in views.py**

In `backend/market_data/views.py`, add the shared field map and the new view class. Place them right before `BrandDominanceView`:

```python
_EVOLUTION_FIELD_MAP = {
    'brand': 'product__sub_brand__brand__description',
    'product': 'product__description',
    'market': 'market__description',
}


class EvolutionOptionsView(APIView):
    def get(self, request):
        category = request.query_params.get('category', '')
        field = _EVOLUTION_FIELD_MAP.get(category)
        if field is None:
            return Response({'error': 'Invalid category'}, status=400)

        values = (
            Data.objects.filter(**{f'{field}__isnull': False})
            .exclude(**{field: ''})
            .order_by(field)
            .values_list(field, flat=True)
            .distinct()
        )
        return Response(list(values))
```

- [ ] **Step 4: Wire the URL**

Replace the contents of `backend/market_data/urls.py` with:

```python
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BrandDominanceView, DataTableFormatViewSet, EvolutionOptionsView

router = DefaultRouter(trailing_slash=True)
router.register('table', DataTableFormatViewSet, basename='data-table')

urlpatterns = router.urls + [
    path('dominance/', BrandDominanceView.as_view(), name='brand-dominance'),
    path('evolution/options/', EvolutionOptionsView.as_view(), name='evolution-options'),
]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest market_data/tests/test_evolution.py -v -k "options"
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/market_data/tests/test_evolution.py backend/market_data/views.py backend/market_data/urls.py
git commit -m "feat: add EvolutionOptionsView with tests"
```

---

## Task 2: EvolutionChartView — tests + implementation

**Files:**
- Modify: `backend/market_data/tests/test_evolution.py`
- Modify: `backend/market_data/views.py`
- Modify: `backend/market_data/urls.py`

- [ ] **Step 1: Append failing chart tests**

Add to the end of `backend/market_data/tests/test_evolution.py`:

```python
@pytest.mark.django_db
def test_chart_aggregates_value_by_calendar_year(api_client, market):
    brand, _ = Brand.objects.get_or_create(description='BRD A')
    sub, _ = SubBrand.objects.get_or_create(description='SUB A', brand=brand)
    product, _ = Product.objects.get_or_create(description='PROD A', sub_brand=sub)
    Data.objects.create(market=market, product=product, value=Decimal('1000'),
                        date=datetime.date(2020, 3, 1), period_weeks=4)
    Data.objects.create(market=market, product=product, value=Decimal('2000'),
                        date=datetime.date(2020, 9, 1), period_weeks=4)
    Data.objects.create(market=market, product=product, value=Decimal('3000'),
                        date=datetime.date(2021, 1, 1), period_weeks=4)

    response = api_client.get('/market-data/evolution/chart/?category=brand&value=BRD A')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0] == {'year': 2020, 'total': '3000.00'}
    assert data[1] == {'year': 2021, 'total': '3000.00'}


@pytest.mark.django_db
def test_chart_results_sorted_ascending_by_year(api_client, market):
    brand, _ = Brand.objects.get_or_create(description='BRD B')
    sub, _ = SubBrand.objects.get_or_create(description='SUB B', brand=brand)
    product, _ = Product.objects.get_or_create(description='PROD B', sub_brand=sub)
    Data.objects.create(market=market, product=product, value=Decimal('500'),
                        date=datetime.date(2022, 1, 1), period_weeks=4)
    Data.objects.create(market=market, product=product, value=Decimal('100'),
                        date=datetime.date(2019, 1, 1), period_weeks=4)

    response = api_client.get('/market-data/evolution/chart/?category=brand&value=BRD B')

    assert response.status_code == 200
    data = response.json()
    assert data[0]['year'] == 2019
    assert data[1]['year'] == 2022


@pytest.mark.django_db
def test_chart_missing_value_param_returns_400(api_client):
    response = api_client.get('/market-data/evolution/chart/?category=brand')
    assert response.status_code == 400


@pytest.mark.django_db
def test_chart_unknown_category_returns_400(api_client):
    response = api_client.get('/market-data/evolution/chart/?category=foo&value=bar')
    assert response.status_code == 400


@pytest.mark.django_db
def test_chart_excludes_rows_with_empty_brand(api_client, market):
    real_brand, _ = Brand.objects.get_or_create(description='REAL')
    empty_brand, _ = Brand.objects.get_or_create(description='')
    for brand_obj, prod_name in [(real_brand, 'PROD R'), (empty_brand, 'PROD E')]:
        sub, _ = SubBrand.objects.get_or_create(description=f'SUB_{prod_name}', brand=brand_obj)
        product, _ = Product.objects.get_or_create(description=prod_name, sub_brand=sub)
        Data.objects.create(market=market, product=product, value=Decimal('1000'),
                            date=datetime.date(2020, 1, 1), period_weeks=4)

    response = api_client.get('/market-data/evolution/chart/?category=brand&value=REAL')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert Decimal(data[0]['total']) == Decimal('1000')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest market_data/tests/test_evolution.py -v -k "chart"
```

Expected: 5 failures — 404 Not Found.

- [ ] **Step 3: Implement EvolutionChartView in views.py**

Add `ExtractYear` to the existing `django.db.models.functions` import line at the top of `backend/market_data/views.py`. The file currently has no functions import, so add:

```python
from django.db.models.functions import ExtractYear
```

Then add `EvolutionChartView` after `EvolutionOptionsView`:

```python
class EvolutionChartView(APIView):
    def get(self, request):
        category = request.query_params.get('category', '')
        value = request.query_params.get('value', '')
        field = _EVOLUTION_FIELD_MAP.get(category)
        if field is None or not value:
            return Response({'error': 'Invalid parameters'}, status=400)

        qs = (
            Data.objects.filter(**{field: value})
            .filter(**{f'{field}__isnull': False})
            .exclude(**{field: ''})
            .annotate(year=ExtractYear('date'))
            .values('year')
            .annotate(total=Sum('value'))
            .order_by('year')
        )
        results = [{'year': row['year'], 'total': str(row['total'])} for row in qs]
        return Response(results)
```

- [ ] **Step 4: Wire the URL**

Update `backend/market_data/urls.py` to import and register `EvolutionChartView`:

```python
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BrandDominanceView, DataTableFormatViewSet, EvolutionOptionsView, EvolutionChartView

router = DefaultRouter(trailing_slash=True)
router.register('table', DataTableFormatViewSet, basename='data-table')

urlpatterns = router.urls + [
    path('dominance/', BrandDominanceView.as_view(), name='brand-dominance'),
    path('evolution/options/', EvolutionOptionsView.as_view(), name='evolution-options'),
    path('evolution/chart/', EvolutionChartView.as_view(), name='evolution-chart'),
]
```

- [ ] **Step 5: Run all evolution tests**

```bash
cd backend && python -m pytest market_data/tests/test_evolution.py -v
```

Expected: 10 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/market_data/tests/test_evolution.py backend/market_data/views.py backend/market_data/urls.py
git commit -m "feat: add EvolutionChartView with tests"
```

---

## Task 3: Frontend route and nav link

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/components/Layout.test.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/Evolution.tsx` (stub — full implementation in Task 4)

- [ ] **Step 1: Write failing nav link tests**

Append to `frontend/src/components/Layout.test.tsx`:

```tsx
test('evolution link shows active indicator at /evolution', () => {
  renderAt('/evolution')
  const link = screen.getByRole('link', { name: /evolution/i })
  expect(link).toHaveClass('border-b-2', 'border-nav-accent', 'pb-0.5')
})

test('evolution link has no active indicator when not at /evolution', () => {
  renderAt('/')
  const link = screen.getByRole('link', { name: /evolution/i })
  expect(link).not.toHaveClass('border-b-2')
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test -- --testPathPattern=Layout --watchAll=false
```

Expected: 2 failures — evolution link not found.

- [ ] **Step 3: Add Evolution nav link to Layout.tsx**

In `frontend/src/components/Layout.tsx`, add after the Dominance `RouterLink`:

```tsx
<RouterLink
  to="/evolution"
  aria-current={pathname === '/evolution' ? 'page' : undefined}
  className={`text-nav-accent no-underline ml-4 text-sm ${pathname === '/evolution' ? 'border-b-2 border-nav-accent pb-0.5' : ''}`}
>
  Evolution
</RouterLink>
```

- [ ] **Step 4: Create Evolution.tsx stub**

Create `frontend/src/pages/Evolution.tsx` with a minimal stub so App.tsx compiles — the full implementation replaces this in Task 4:

```tsx
function Evolution() {
  return <div>Evolution</div>
}

export default Evolution
```

- [ ] **Step 5: Add /evolution route to App.tsx**

Replace `frontend/src/App.tsx` with:

```tsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Explore from './pages/Explore'
import Dominance from './pages/Dominance'
import Evolution from './pages/Evolution'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/explore" element={<Explore />} />
        <Route path="/dominance" element={<Dominance />} />
        <Route path="/evolution" element={<Evolution />} />
      </Route>
    </Routes>
  )
}

export default App
```

- [ ] **Step 6: Run Layout tests**

```bash
cd frontend && npm test -- --testPathPattern=Layout --watchAll=false
```

Expected: all Layout tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Layout.tsx frontend/src/components/Layout.test.tsx frontend/src/App.tsx frontend/src/pages/Evolution.tsx
git commit -m "feat: wire /evolution route and nav link"
```

---

## Task 4: Evolution page — initial state (selectors + placeholder)

**Files:**
- Create: `frontend/src/pages/Evolution.test.tsx`
- Modify: `frontend/src/pages/Evolution.tsx` (replace stub with full implementation)

- [ ] **Step 1: Write failing tests for initial render**

Create `frontend/src/pages/Evolution.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Evolution from './Evolution'
import apiClient from '../api/client'

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ data }: { data: Array<{ year: number }> }) => (
    <div data-testid="bar-chart">
      {data?.map((d) => (
        <div key={d.year} data-testid="bar-year">
          {d.year}
        </div>
      ))}
    </div>
  ),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

jest.mock('../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}))
const mockedGet = apiClient.get as jest.Mock

function renderPage() {
  return render(
    <MemoryRouter>
      <Evolution />
    </MemoryRouter>
  )
}

describe('Evolution page — initial state', () => {
  beforeEach(() => mockedGet.mockReset())
  afterEach(() => jest.clearAllMocks())

  it('renders Category and Value selects', () => {
    renderPage()
    expect(screen.getByRole('combobox', { name: 'Category' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Value' })).toBeInTheDocument()
  })

  it('shows placeholder message before any selection', () => {
    renderPage()
    expect(
      screen.getByText('Select a category and a value to see the evolution chart.')
    ).toBeInTheDocument()
  })

  it('Value select is disabled before category is chosen', () => {
    renderPage()
    expect(screen.getByRole('combobox', { name: 'Value' })).toHaveAttribute('aria-disabled', 'true')
  })

  it('does not call the API on initial render', () => {
    renderPage()
    expect(mockedGet).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test -- --testPathPattern="pages/Evolution" --watchAll=false
```

Expected: 4 failures (stub renders `<div>Evolution</div>`, none of the queries match).

- [ ] **Step 3: Replace Evolution.tsx stub with full implementation**

Replace `frontend/src/pages/Evolution.tsx` with:

```tsx
import { useState, useEffect } from 'react'
import {
  Box,
  CircularProgress,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Typography,
} from '@mui/material'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import apiClient from '../api/client'

type Category = 'brand' | 'product' | 'market' | ''

type ChartRow = {
  year: number
  total: number
}

function Evolution() {
  const [category, setCategory] = useState<Category>('')
  const [options, setOptions] = useState<string[]>([])
  const [selectedValue, setSelectedValue] = useState('')
  const [chartData, setChartData] = useState<ChartRow[]>([])
  const [loadingOptions, setLoadingOptions] = useState(false)
  const [loadingChart, setLoadingChart] = useState(false)

  useEffect(() => {
    if (!category) return
    let cancelled = false
    setLoadingOptions(true)
    apiClient
      .get<string[]>(`/market-data/evolution/options/?category=${category}`)
      .then(({ data }) => {
        if (!cancelled) {
          setOptions(data)
          setLoadingOptions(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoadingOptions(false)
      })
    return () => {
      cancelled = true
    }
  }, [category])

  useEffect(() => {
    if (!category || !selectedValue) return
    let cancelled = false
    setLoadingChart(true)
    apiClient
      .get<{ year: number; total: string }[]>(
        `/market-data/evolution/chart/?category=${category}&value=${encodeURIComponent(selectedValue)}`
      )
      .then(({ data }) => {
        if (!cancelled) {
          setChartData(data.map((r) => ({ year: r.year, total: parseFloat(r.total) })))
          setLoadingChart(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoadingChart(false)
      })
    return () => {
      cancelled = true
    }
  }, [category, selectedValue])

  const handleCategoryChange = (value: Category) => {
    setCategory(value)
    setSelectedValue('')
    setChartData([])
    setOptions([])
  }

  const bothSelected = category !== '' && selectedValue !== ''

  return (
    <Container maxWidth="xl" className="py-8">
      <Typography variant="h4" component="h1" className="pb-6">
        Sales Evolution
      </Typography>
      <div className="flex gap-4 pb-6">
        <FormControl sx={{ minWidth: 180 }}>
          <InputLabel id="category-label">Category</InputLabel>
          <Select
            labelId="category-label"
            label="Category"
            value={category}
            onChange={(e) => handleCategoryChange(e.target.value as Category)}
          >
            <MenuItem value="brand">Brand</MenuItem>
            <MenuItem value="product">Product</MenuItem>
            <MenuItem value="market">Market</MenuItem>
          </Select>
        </FormControl>
        <FormControl sx={{ minWidth: 220 }} disabled={!category || loadingOptions}>
          <InputLabel id="value-label">Value</InputLabel>
          <Select
            labelId="value-label"
            label="Value"
            value={selectedValue}
            onChange={(e) => setSelectedValue(e.target.value)}
          >
            {options.map((opt) => (
              <MenuItem key={opt} value={opt}>
                {opt}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </div>
      {!bothSelected && (
        <Box className="flex justify-center py-16">
          <Typography color="text.secondary">
            Select a category and a value to see the evolution chart.
          </Typography>
        </Box>
      )}
      {bothSelected && loadingChart && (
        <Box className="flex justify-center py-4">
          <CircularProgress />
        </Box>
      )}
      {bothSelected && !loadingChart && chartData.length === 0 && (
        <Box className="flex justify-center py-4">
          <Typography>No data available</Typography>
        </Box>
      )}
      {bothSelected && !loadingChart && chartData.length > 0 && (
        <Paper className="p-4">
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis
                tickFormatter={(v: number) =>
                  v.toLocaleString('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    maximumFractionDigits: 0,
                  })
                }
              />
              <Bar dataKey="total" />
              <Tooltip
                formatter={(v: number) =>
                  v.toLocaleString('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    maximumFractionDigits: 0,
                  })
                }
              />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      )}
    </Container>
  )
}

export default Evolution
```

- [ ] **Step 4: Run initial-state tests**

```bash
cd frontend && npm test -- --testPathPattern="pages/Evolution" --watchAll=false
```

Expected: 4 initial-state tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Evolution.tsx frontend/src/pages/Evolution.test.tsx
git commit -m "feat: add Evolution page with selectors and placeholder"
```

---

## Task 5: Evolution page — options fetch after category select

**Files:**
- Modify: `frontend/src/pages/Evolution.test.tsx`

- [ ] **Step 1: Append failing tests**

Add to `frontend/src/pages/Evolution.test.tsx` after the initial-state `describe` block:

```tsx
describe('Evolution page — options fetch', () => {
  beforeEach(() => mockedGet.mockReset())
  afterEach(() => jest.clearAllMocks())

  it('fetches brand options and enables Value select after Category is chosen', async () => {
    mockedGet.mockResolvedValue({ data: ['Brand A', 'Brand B'] })
    renderPage()

    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand' }))

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        '/market-data/evolution/options/?category=brand'
      )
    )

    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Value' })).not.toHaveAttribute('aria-disabled', 'true')
    )

    await userEvent.click(screen.getByRole('combobox', { name: 'Value' }))
    expect(await screen.findByRole('option', { name: 'Brand A' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Brand B' })).toBeInTheDocument()
  })

  it('Value select stays disabled while options are loading', async () => {
    mockedGet.mockReturnValue(new Promise(() => {}))
    renderPage()

    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Market' }))

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        '/market-data/evolution/options/?category=market'
      )
    )

    expect(screen.getByRole('combobox', { name: 'Value' })).toHaveAttribute('aria-disabled', 'true')
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm test -- --testPathPattern="pages/Evolution" --watchAll=false
```

Expected: all tests pass — the options-fetch `useEffect` is already in Evolution.tsx.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Evolution.test.tsx
git commit -m "test: add options-fetch tests for Evolution page"
```

---

## Task 6: Evolution page — chart renders after both selectors set

**Files:**
- Modify: `frontend/src/pages/Evolution.test.tsx`

- [ ] **Step 1: Append failing tests**

Add to `frontend/src/pages/Evolution.test.tsx`:

```tsx
describe('Evolution page — chart render', () => {
  beforeEach(() => mockedGet.mockReset())
  afterEach(() => jest.clearAllMocks())

  it('renders bar chart with year data after both selectors are set', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url.includes('options')) return Promise.resolve({ data: ['Brand A'] })
      if (url.includes('chart')) {
        return Promise.resolve({
          data: [
            { year: 2020, total: '1000.00' },
            { year: 2021, total: '2000.00' },
          ],
        })
      }
      return Promise.reject(new Error(`unexpected url: ${url}`))
    })
    renderPage()

    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand' }))
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Value' })).not.toHaveAttribute('aria-disabled', 'true')
    )
    await userEvent.click(screen.getByRole('combobox', { name: 'Value' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand A' }))

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        '/market-data/evolution/chart/?category=brand&value=Brand%20A'
      )
    )

    expect(await screen.findByTestId('bar-chart')).toBeInTheDocument()
    expect(screen.getByText('2020')).toBeInTheDocument()
    expect(screen.getByText('2021')).toBeInTheDocument()
  })

  it('shows No data available when chart endpoint returns empty array', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url.includes('options')) return Promise.resolve({ data: ['Brand A'] })
      if (url.includes('chart')) return Promise.resolve({ data: [] })
      return Promise.reject(new Error(`unexpected url: ${url}`))
    })
    renderPage()

    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand' }))
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Value' })).not.toHaveAttribute('aria-disabled', 'true')
    )
    await userEvent.click(screen.getByRole('combobox', { name: 'Value' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand A' }))

    await waitFor(() => expect(screen.getByText('No data available')).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm test -- --testPathPattern="pages/Evolution" --watchAll=false
```

Expected: all tests pass — chart logic is already in Evolution.tsx.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Evolution.test.tsx
git commit -m "test: add chart-render tests for Evolution page"
```

---

## Task 7: Evolution page — category change resets state

**Files:**
- Modify: `frontend/src/pages/Evolution.test.tsx`

- [ ] **Step 1: Append failing test**

Add to `frontend/src/pages/Evolution.test.tsx`:

```tsx
describe('Evolution page — category reset', () => {
  beforeEach(() => mockedGet.mockReset())
  afterEach(() => jest.clearAllMocks())

  it('resets Value select and clears chart when Category changes after chart is shown', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url.includes('options')) return Promise.resolve({ data: ['Brand A'] })
      if (url.includes('chart')) {
        return Promise.resolve({ data: [{ year: 2020, total: '1000.00' }] })
      }
      return Promise.reject(new Error(`unexpected url: ${url}`))
    })
    renderPage()

    // Select Brand → Brand A → chart appears
    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand' }))
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Value' })).not.toHaveAttribute('aria-disabled', 'true')
    )
    await userEvent.click(screen.getByRole('combobox', { name: 'Value' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand A' }))
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument())

    // Change Category to Market
    mockedGet.mockResolvedValue({ data: ['Market 1'] })
    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Market' }))

    // Chart disappears and placeholder returns
    await waitFor(() =>
      expect(
        screen.getByText('Select a category and a value to see the evolution chart.')
      ).toBeInTheDocument()
    )
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument()

    // Value select is disabled again (no value selected)
    expect(screen.getByRole('combobox', { name: 'Value' })).toHaveAttribute('aria-disabled', 'true')
  })
})
```

- [ ] **Step 2: Run all Evolution tests**

```bash
cd frontend && npm test -- --testPathPattern="pages/Evolution" --watchAll=false
```

Expected: all Evolution tests pass — `handleCategoryChange` already clears state in Evolution.tsx.

- [ ] **Step 3: Run full frontend test suite for regressions**

```bash
cd frontend && npm test -- --watchAll=false
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Evolution.test.tsx
git commit -m "test: add category-reset tests for Evolution page"
```
