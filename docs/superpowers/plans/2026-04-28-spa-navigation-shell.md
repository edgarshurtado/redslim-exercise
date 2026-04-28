# SPA Navigation Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dark MUI navbar and React Router v6 SPA shell with a landing page and an Explore placeholder page.

**Architecture:** A `Layout` component holds the `AppBar` and renders child routes via `<Outlet />`. `App.tsx` owns the route configuration. `BrowserRouter` wraps `App` in `main.tsx`. Current landing content moves from `App.tsx` into `pages/Landing.tsx`.

**Tech Stack:** React 19, React Router v7, MUI v9, TypeScript, Jest + Testing Library

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `frontend/src/pages/Landing.tsx` | Create | Landing page (current App content) |
| `frontend/src/pages/Explore.tsx` | Create | Placeholder explore page |
| `frontend/src/components/Layout.tsx` | Create | AppBar + Outlet shared layout |
| `frontend/src/App.tsx` | Modify | Replace with route config |
| `frontend/src/main.tsx` | Modify | Wrap App in BrowserRouter |
| `frontend/src/Landing.test.tsx` | Create | Landing page unit tests |
| `frontend/src/App.test.tsx` | Modify | Replace with routing integration tests |

---

## Task 1: Install react-router-dom

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install the package**

```bash
cd frontend && npm install react-router-dom
```

Expected: resolves without errors, `react-router-dom` appears in `package.json` dependencies.

- [ ] **Step 2: Verify types are available**

`react-router-dom` v6 ships its own TypeScript types — no separate `@types` package needed. Verify:

```bash
cd frontend && npx tsc --noEmit
```

Expected: exits 0 (no type errors).

- [ ] **Step 3: Commit**

```bash
cd frontend && git add package.json package-lock.json && git commit -m "feat: add react-router-dom"
```

---

## Task 2: Extract landing page (TDD)

**Files:**
- Create: `frontend/src/pages/Landing.tsx`
- Create: `frontend/src/Landing.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/Landing.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import Landing from './pages/Landing'
import apiClient from './api/client'

jest.mock('./api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() }
}))

beforeEach(() => {
  jest.mocked(apiClient.get).mockReset()
})

test('renders Hello Redslim heading', () => {
  jest.mocked(apiClient.get).mockReturnValue(new Promise(() => {}))
  render(<Landing />)
  expect(screen.getByRole('heading', { name: /hello redslim/i })).toBeInTheDocument()
})

test('displays API response message', async () => {
  jest.mocked(apiClient.get).mockResolvedValue({ data: { message: 'Hello Redslim' } })
  render(<Landing />)
  await waitFor(() => {
    expect(screen.getByTestId('api-message')).toHaveTextContent('Hello Redslim')
  })
})

test('displays error message when API fails', async () => {
  jest.mocked(apiClient.get).mockRejectedValue(new Error('Network Error'))
  render(<Landing />)
  await waitFor(() => {
    expect(screen.getByTestId('api-message')).toHaveTextContent('Could not reach the server.')
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd frontend && npx jest Landing.test --no-coverage
```

Expected: FAIL — `Cannot find module './pages/Landing'`

- [ ] **Step 3: Create pages/Landing.tsx**

Create `frontend/src/pages/Landing.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { Typography, Container, Box } from '@mui/material'
import apiClient from '../api/client'

function Landing() {
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    apiClient.get('/redslim-hello')
      .then(res => setMessage(res.data.message))
      .catch(() => setMessage('Could not reach the server.'))
  }, [])

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Typography variant="h2" component="h1">
          Hello Redslim
        </Typography>
        {message && (
          <Typography variant="body1" data-testid="api-message">
            {message}
          </Typography>
        )}
      </Box>
    </Container>
  )
}

export default Landing
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
cd frontend && npx jest Landing.test --no-coverage
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd frontend && git add src/pages/Landing.tsx src/Landing.test.tsx && git commit -m "feat: extract landing page to pages/Landing"
```

---

## Task 3: Create Explore placeholder

**Files:**
- Create: `frontend/src/pages/Explore.tsx`

No standalone tests — the Explore route is covered by the routing tests in Task 5.

- [ ] **Step 1: Create pages/Explore.tsx**

```tsx
import { Typography, Container, Box } from '@mui/material'

function Explore() {
  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Typography variant="h4" component="h1">
          Explore
        </Typography>
      </Box>
    </Container>
  )
}

export default Explore
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/pages/Explore.tsx && git commit -m "feat: add Explore placeholder page"
```

---

## Task 4: Create Layout component

**Files:**
- Create: `frontend/src/components/Layout.tsx`

No standalone tests — Layout is covered by routing tests in Task 5.

- [ ] **Step 1: Create components/Layout.tsx**

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
            style={{
              color: '#fff',
              fontWeight: 700,
              fontSize: '16px',
              letterSpacing: '0.3px',
              textDecoration: 'none',
            }}
          >
            Edgar's ReadSlim Exercise
          </RouterLink>
          <RouterLink
            to="/explore"
            style={{
              color: '#90caf9',
              textDecoration: 'none',
              marginLeft: '16px',
              fontSize: '14px',
              ...(pathname === '/explore' && { borderBottom: '2px solid #90caf9' }),
            }}
          >
            Explore
          </RouterLink>
        </Toolbar>
      </AppBar>
      <Outlet />
    </>
  )
}

export default Layout
```

- [ ] **Step 2: Commit**

```bash
cd frontend && git add src/components/Layout.tsx && git commit -m "feat: add Layout component with dark AppBar"
```

---

## Task 5: Wire up routing (TDD)

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing routing tests**

Replace the contents of `frontend/src/App.test.tsx` with:

```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import apiClient from './api/client'

jest.mock('./api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() }
}))

beforeEach(() => {
  jest.mocked(apiClient.get).mockReturnValue(new Promise(() => {}))
})

test('renders Landing page at /', () => {
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>
  )
  expect(screen.getByRole('heading', { name: /hello redslim/i })).toBeInTheDocument()
})

test('renders Explore page at /explore', () => {
  render(
    <MemoryRouter initialEntries={['/explore']}>
      <App />
    </MemoryRouter>
  )
  expect(screen.getByRole('heading', { name: /explore/i })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd frontend && npx jest App.test --no-coverage
```

Expected: FAIL — App still renders the old content, not via routes.

- [ ] **Step 3: Rewrite App.tsx as route config**

Replace the contents of `frontend/src/App.tsx` with:

```tsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Explore from './pages/Explore'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/explore" element={<Explore />} />
      </Route>
    </Routes>
  )
}

export default App
```

- [ ] **Step 4: Update main.tsx to wrap App in BrowserRouter**

Replace the contents of `frontend/src/main.tsx` with:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
```

- [ ] **Step 5: Run routing tests to confirm pass**

```bash
cd frontend && npx jest App.test --no-coverage
```

Expected: 2 tests PASS.

- [ ] **Step 6: Run the full test suite**

```bash
cd frontend && npx jest --no-coverage
```

Expected: all tests PASS (Landing.test + App.test).

- [ ] **Step 7: Commit**

```bash
cd frontend && git add src/App.tsx src/main.tsx src/App.test.tsx && git commit -m "feat: wire up React Router SPA shell"
```

---

## Task 6: Add .superpowers to .gitignore

**Files:**
- Modify: `frontend/.gitignore` or root `.gitignore`

- [ ] **Step 1: Add .superpowers/ to root .gitignore**

Open the root `.gitignore` and add this line:

```
.superpowers/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore && git commit -m "chore: ignore .superpowers brainstorm directory"
```
