# Manufacturer Dominance Treemap — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/dominance` page with a Recharts treemap showing brand dominance — box size = total sales value, box color = sales-weighted average WTD on a green→red scale.

**Architecture:** A new `BrandDominanceView` (Django APIView) aggregates `Data` rows by brand using ORM annotations, computing total sales and sales-weighted average WTD in a single query plus Python division. A new `Dominance.tsx` React page fetches this endpoint on mount, computes color interpolation on the client, and renders a Recharts `Treemap` with a custom cell renderer and tooltip. Nav bar and routing are extended to expose `/dominance`.

**Tech Stack:** Django REST Framework (APIView, Response), Recharts (Treemap, ResponsiveContainer, Tooltip), MUI (Container, Typography, Paper, CircularProgress), React Router DOM.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/market_data/tests/test_dominance.py` | Create | Backend endpoint tests |
| `backend/market_data/views.py` | Modify | Add `BrandDominanceView` |
| `backend/market_data/urls.py` | Modify | Register `dominance/` route |
| `frontend/src/pages/Dominance.test.tsx` | Create | Frontend component tests |
| `frontend/src/pages/Dominance.tsx` | Create | Treemap page component |
| `frontend/src/App.tsx` | Modify | Add `/dominance` route |
| `frontend/src/components/Layout.tsx` | Modify | Add Dominance nav link |
| `frontend/package.json` | Modify (via npm install) | Add `recharts` dependency |

---

### Task 1: Write failing backend tests

**Files:**
- Create: `backend/market_data/tests/test_dominance.py`

- [ ] **Step 1: Create the test file**

Create `backend/market_data/tests/test_dominance.py`:

```python
import datetime
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from market_data.models import Brand, SubBrand, Product, Market, Data


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def market():
    return Market.objects.create(description='MARKET1', description_2='TOT RETAILER 1')


def _make_brand(brand_name, sub_name, product_name, market, rows):
    """rows: list of (value, wtd_or_none, date) tuples."""
    brand, _ = Brand.objects.get_or_create(description=brand_name)
    sub, _ = SubBrand.objects.get_or_create(description=sub_name, brand=brand)
    product, _ = Product.objects.get_or_create(description=product_name, sub_brand=sub)
    for value, wtd, date in rows:
        Data.objects.create(
            market=market,
            product=product,
            value=Decimal(str(value)),
            weighted_distribution=Decimal(str(wtd)) if wtd is not None else None,
            date=date,
            period_weeks=4,
        )
    return brand


@pytest.mark.django_db
def test_happy_path(client, market):
    # weighted avg WTD = (1000*40 + 3000*60) / (1000+3000) = 220000/4000 = 55.00
    _make_brand('BRAND A', 'SUB A', 'PROD A', market, [
        (1000, 40, datetime.date(2016, 9, 4)),
        (3000, 60, datetime.date(2016, 9, 11)),
    ])

    response = client.get('/market-data/dominance/')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['brand'] == 'BRAND A'
    assert Decimal(data[0]['total_value']) == Decimal('4000')
    assert abs(Decimal(data[0]['weighted_avg_wtd']) - Decimal('55.00')) < Decimal('0.01')


@pytest.mark.django_db
def test_all_null_wtd_returns_null(client, market):
    _make_brand('BRAND NULL', 'SUB N', 'PROD N', market, [
        (1000, None, datetime.date(2016, 9, 4)),
        (2000, None, datetime.date(2016, 9, 11)),
    ])

    response = client.get('/market-data/dominance/')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['weighted_avg_wtd'] is None


@pytest.mark.django_db
def test_mixed_null_wtd_uses_only_non_null_rows(client, market):
    # Only the non-null row contributes to the weighted average: (2000*60) / 2000 = 60.00
    _make_brand('BRAND MIX', 'SUB M', 'PROD M', market, [
        (1000, None, datetime.date(2016, 9, 4)),
        (2000, 60, datetime.date(2016, 9, 11)),
    ])

    response = client.get('/market-data/dominance/')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert abs(Decimal(data[0]['weighted_avg_wtd']) - Decimal('60.00')) < Decimal('0.01')


@pytest.mark.django_db
def test_ordered_by_total_value_descending(client, market):
    _make_brand('SMALL', 'SUB S', 'PROD S', market, [(500, 30, datetime.date(2016, 9, 4))])
    _make_brand('BIG', 'SUB B', 'PROD B', market, [(9000, 70, datetime.date(2016, 9, 4))])

    response = client.get('/market-data/dominance/')

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['brand'] == 'BIG'
    assert data[1]['brand'] == 'SMALL'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/rumil/repos/redslim-exercise/backend && venv/bin/pytest market_data/tests/test_dominance.py -v
```

Expected: 4 failures — `404 Not Found` (endpoint doesn't exist yet).

---

### Task 2: Implement the backend endpoint

**Files:**
- Modify: `backend/market_data/views.py`
- Modify: `backend/market_data/urls.py`

- [ ] **Step 1: Add imports and `BrandDominanceView` to `views.py`**

The current imports at the top of `backend/market_data/views.py` are:
```python
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from market_data.models import Data
```

Replace them with:
```python
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from market_data.models import Data
```

Then append this class at the bottom of `backend/market_data/views.py`:

```python
class BrandDominanceView(APIView):
    def get(self, request):
        qs = Data.objects.values(
            brand=F('product__sub_brand__brand__description')
        ).annotate(
            total_value=Sum('value'),
            wtd_numerator=Sum(
                ExpressionWrapper(
                    F('value') * F('weighted_distribution'),
                    output_field=DecimalField(max_digits=20, decimal_places=4),
                ),
                filter=Q(weighted_distribution__isnull=False),
            ),
            wtd_denominator=Sum(
                'value',
                filter=Q(weighted_distribution__isnull=False),
            ),
        ).order_by('-total_value')

        results = []
        for row in qs:
            wtd = None
            if row['wtd_numerator'] is not None and row['wtd_denominator']:
                wtd = (row['wtd_numerator'] / row['wtd_denominator']).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            results.append({
                'brand': row['brand'],
                'total_value': str(row['total_value']),
                'weighted_avg_wtd': str(wtd) if wtd is not None else None,
            })

        return Response(results)
```

- [ ] **Step 2: Register the route in `urls.py`**

Replace the entire content of `backend/market_data/urls.py` with:

```python
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BrandDominanceView, DataTableFormatViewSet

router = DefaultRouter(trailing_slash=True)
router.register('table', DataTableFormatViewSet, basename='data-table')

urlpatterns = router.urls + [
    path('dominance/', BrandDominanceView.as_view()),
]
```

- [ ] **Step 3: Run the dominance tests**

```bash
cd /home/rumil/repos/redslim-exercise/backend && venv/bin/pytest market_data/tests/test_dominance.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Run full test suite to check for regressions**

```bash
cd /home/rumil/repos/redslim-exercise/backend && venv/bin/pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/market_data/views.py backend/market_data/urls.py backend/market_data/tests/test_dominance.py
git commit -m "feat: add BrandDominanceView aggregation endpoint"
```

---

### Task 3: Write failing frontend tests

**Files:**
- Create: `frontend/src/pages/Dominance.test.tsx`

- [ ] **Step 1: Create the test file**

Create `frontend/src/pages/Dominance.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Dominance from './Dominance'
import apiClient from '../api/client'

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Treemap: ({ data }: { data: Array<{ name: string }> }) => (
    <div data-testid="treemap">
      {data?.map((d) => (
        <div key={d.name} data-testid="treemap-cell">
          {d.name}
        </div>
      ))}
    </div>
  ),
  Tooltip: () => null,
}))

jest.mock('../api/client')
const mockedGet = apiClient.get as jest.Mock

const BRAND_DATA = [
  { brand: 'BRAND A', total_value: '4000.00', weighted_avg_wtd: '55.00' },
  { brand: 'BRAND B', total_value: '1000.00', weighted_avg_wtd: null },
]

function renderPage() {
  return render(
    <MemoryRouter>
      <Dominance />
    </MemoryRouter>
  )
}

describe('Dominance page', () => {
  afterEach(() => jest.clearAllMocks())

  it('shows loading spinner while fetching', () => {
    mockedGet.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('renders brand names after successful fetch', async () => {
    mockedGet.mockResolvedValue({ data: BRAND_DATA })
    renderPage()
    await waitFor(() => expect(screen.queryByRole('progressbar')).not.toBeInTheDocument())
    expect(screen.getByText('BRAND A')).toBeInTheDocument()
    expect(screen.getByText('BRAND B')).toBeInTheDocument()
  })

  it('shows no data message for empty response', async () => {
    mockedGet.mockResolvedValue({ data: [] })
    renderPage()
    await waitFor(() => expect(screen.getByText('No data available')).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /home/rumil/repos/redslim-exercise/frontend && npx jest --testPathPattern=Dominance --watchAll=false
```

Expected: 3 failures — `Cannot find module './Dominance'`.

---

### Task 4: Implement the Dominance page and wire routing

**Files:**
- Create: `frontend/src/pages/Dominance.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/package.json` (via npm install)

- [ ] **Step 1: Install recharts**

```bash
cd /home/rumil/repos/redslim-exercise/frontend && npm install recharts
```

Expected: `recharts` appears in `frontend/package.json` dependencies.

- [ ] **Step 2: Create `frontend/src/pages/Dominance.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { Box, CircularProgress, Container, Paper, Typography } from '@mui/material'
import { ResponsiveContainer, Treemap, Tooltip } from 'recharts'
import apiClient from '../api/client'

type BrandDatum = {
  brand: string
  total_value: string
  weighted_avg_wtd: string | null
}

type TreemapNode = {
  name: string
  size: number
  fill: string
  wtd: number | null
}

function interpolateColor(t: number): string {
  const green = { r: 0x2e, g: 0x7d, b: 0x32 }
  const red = { r: 0xc6, g: 0x28, b: 0x28 }
  const r = Math.round(green.r + (red.r - green.r) * t)
  const g = Math.round(green.g + (red.g - green.g) * t)
  const b = Math.round(green.b + (red.b - green.b) * t)
  return `rgb(${r},${g},${b})`
}

function toChartData(data: BrandDatum[]): TreemapNode[] {
  const wtdValues = data
    .map((d) => (d.weighted_avg_wtd !== null ? parseFloat(d.weighted_avg_wtd) : null))
    .filter((v): v is number => v !== null)

  const minWtd = wtdValues.length ? Math.min(...wtdValues) : 0
  const maxWtd = wtdValues.length ? Math.max(...wtdValues) : 100
  const range = maxWtd - minWtd || 1

  return data.map((d) => {
    const wtd = d.weighted_avg_wtd !== null ? parseFloat(d.weighted_avg_wtd) : null
    const fill = wtd !== null ? interpolateColor((wtd - minWtd) / range) : '#9e9e9e'
    return { name: d.brand, size: parseFloat(d.total_value), fill, wtd }
  })
}

type CellProps = {
  x: number
  y: number
  width: number
  height: number
  name: string
  fill: string
  wtd: number | null
}

function CustomCell({ x, y, width, height, name, fill, wtd }: CellProps) {
  const showLabel = width > 60 && height > 40
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#fff" strokeWidth={2} />
      {showLabel && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - (wtd !== null ? 8 : 0)}
            textAnchor="middle"
            fill="white"
            fontSize={12}
            fontWeight={700}
          >
            {name}
          </text>
          {wtd !== null && (
            <text
              x={x + width / 2}
              y={y + height / 2 + 10}
              textAnchor="middle"
              fill="white"
              fontSize={11}
            >
              {wtd.toFixed(1)}%
            </text>
          )}
        </>
      )}
    </g>
  )
}

type TooltipPayload = { payload: TreemapNode }

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <Paper sx={{ p: 1.5 }}>
      <Typography variant="body2" fontWeight={700}>
        {d.name}
      </Typography>
      <Typography variant="body2">
        Sales:{' '}
        {d.size.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}
      </Typography>
      {d.wtd !== null && (
        <Typography variant="body2">Wtd Dist: {d.wtd.toFixed(1)}%</Typography>
      )}
    </Paper>
  )
}

function Dominance() {
  const [data, setData] = useState<TreemapNode[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient
      .get<BrandDatum[]>('/market-data/dominance/')
      .then(({ data: raw }) => {
        setData(toChartData(raw))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  return (
    <Container maxWidth="xl" className="py-8">
      <div className="pb-1">
        <Typography variant="h4" component="h1">
          Manufacturer Dominance
        </Typography>
      </div>
      <Typography variant="body2" color="text.secondary" className="pb-4">
        Box size = total sales value · Box color = sales-weighted distribution (green = lean, red = bloated)
      </Typography>
      <div className="flex items-center gap-2 pb-6">
        <Typography variant="caption" sx={{ color: '#2e7d32', fontWeight: 600 }}>
          Efficient
        </Typography>
        <div
          className="h-2.5 w-40 rounded"
          style={{ background: 'linear-gradient(to right, #2e7d32, #66bb6a, #ef9a9a, #c62828)' }}
        />
        <Typography variant="caption" sx={{ color: '#c62828', fontWeight: 600 }}>
          Bloated
        </Typography>
      </div>
      {loading && (
        <Box className="flex justify-center py-4">
          <CircularProgress />
        </Box>
      )}
      {!loading && data.length === 0 && (
        <Box className="flex justify-center py-4">
          <Typography>No data available</Typography>
        </Box>
      )}
      {!loading && data.length > 0 && (
        <Paper className="p-4">
          <ResponsiveContainer width="100%" height={500}>
            <Treemap
              data={data}
              dataKey="size"
              content={(props: any) => (
                <CustomCell
                  x={props.x}
                  y={props.y}
                  width={props.width}
                  height={props.height}
                  name={props.name}
                  fill={props.fill}
                  wtd={props.wtd}
                />
              )}
            >
              <Tooltip content={<CustomTooltip />} />
            </Treemap>
          </ResponsiveContainer>
        </Paper>
      )}
      <Typography variant="caption" color="text.secondary" className="block pt-3 text-right">
        Aggregated across all markets and periods
      </Typography>
    </Container>
  )
}

export default Dominance
```

- [ ] **Step 3: Add the `/dominance` route to `App.tsx`**

Replace the content of `frontend/src/App.tsx` with:

```tsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Explore from './pages/Explore'
import Dominance from './pages/Dominance'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/explore" element={<Explore />} />
        <Route path="/dominance" element={<Dominance />} />
      </Route>
    </Routes>
  )
}

export default App
```

- [ ] **Step 4: Add the Dominance nav link to `Layout.tsx`**

Replace the content of `frontend/src/components/Layout.tsx` with:

```tsx
import { AppBar, Toolbar } from '@mui/material'
import { Link as RouterLink, Outlet, useLocation } from 'react-router-dom'

function Layout() {
  const { pathname } = useLocation()

  return (
    <>
      <AppBar position="static" sx={{ backgroundColor: '#1a1a2e' }}>
        <Toolbar sx={{ px: 4 }}>
          <RouterLink
            to="/"
            aria-current={pathname === '/' ? 'page' : undefined}
            className="text-white font-bold text-base tracking-[0.3px] no-underline"
          >
            Edgar's ReadSlim Exercise
          </RouterLink>
          <RouterLink
            to="/explore"
            aria-current={pathname === '/explore' ? 'page' : undefined}
            className={`text-nav-accent no-underline ml-4 text-sm ${pathname === '/explore' ? 'border-b-2 border-nav-accent pb-0.5' : ''}`}
          >
            Explore
          </RouterLink>
          <RouterLink
            to="/dominance"
            aria-current={pathname === '/dominance' ? 'page' : undefined}
            className={`text-nav-accent no-underline ml-4 text-sm ${pathname === '/dominance' ? 'border-b-2 border-nav-accent pb-0.5' : ''}`}
          >
            Dominance
          </RouterLink>
        </Toolbar>
      </AppBar>
      <Outlet />
    </>
  )
}

export default Layout
```

- [ ] **Step 5: Run the Dominance frontend tests**

```bash
cd /home/rumil/repos/redslim-exercise/frontend && npx jest --testPathPattern=Dominance --watchAll=false
```

Expected: 3 tests pass.

- [ ] **Step 6: Run full frontend test suite to check for regressions**

```bash
cd /home/rumil/repos/redslim-exercise/frontend && npx jest --watchAll=false
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Dominance.tsx frontend/src/pages/Dominance.test.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: add Manufacturer Dominance treemap page"
```
