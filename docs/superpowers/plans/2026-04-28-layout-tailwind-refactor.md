# Layout.tsx Inline Styles → Tailwind Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all inline `style` props in `Layout.tsx` with Tailwind CSS classes, adding a `nav-accent` color token to the Tailwind config.

**Architecture:** Two `RouterLink` components currently use `style` props for all visual styling. We convert those to `className`, add a named color token `nav-accent` (#90caf9) to `tailwind.config.js`, and handle the conditional active-state border via a ternary in the template literal. MUI `sx` props on `AppBar` and `Toolbar` are untouched.

**Tech Stack:** React, Tailwind CSS v3, React Router v6, Jest + @testing-library/react

---

## Files

- **Modify:** `frontend/tailwind.config.js` — add `nav-accent` color token
- **Modify:** `frontend/src/components/Layout.tsx` — replace `style` props with `className`
- **Create:** `frontend/src/components/Layout.test.tsx` — tests for Tailwind classes and conditional active state

---

### Task 1: Write the failing tests for Layout

**Files:**
- Create: `frontend/src/components/Layout.test.tsx`

- [ ] **Step 1: Create `Layout.test.tsx`**

```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Layout from './Layout'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="*" element={<div />} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

test('home link has Tailwind classes and no inline style', () => {
  renderAt('/')
  const homeLink = screen.getByRole('link', { name: /edgar's readslim exercise/i })
  expect(homeLink).toHaveClass('text-white', 'font-bold', 'text-base', 'no-underline')
  expect(homeLink).not.toHaveAttribute('style')
})

test('explore link has Tailwind classes and no inline style', () => {
  renderAt('/')
  const exploreLink = screen.getByRole('link', { name: /explore/i })
  expect(exploreLink).toHaveClass('text-nav-accent', 'no-underline', 'ml-4', 'text-sm')
  expect(exploreLink).not.toHaveAttribute('style')
})

test('explore link shows active indicator at /explore', () => {
  renderAt('/explore')
  const exploreLink = screen.getByRole('link', { name: /explore/i })
  expect(exploreLink).toHaveClass('border-b-2', 'border-nav-accent', 'pb-0.5')
})

test('explore link has no active indicator when not at /explore', () => {
  renderAt('/')
  const exploreLink = screen.getByRole('link', { name: /explore/i })
  expect(exploreLink).not.toHaveClass('border-b-2')
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npx jest src/components/Layout.test.tsx --no-coverage
```

Expected: 4 FAIL — the links still have `style` props, not `className`.

---

### Task 2: Add `nav-accent` color to Tailwind config

**Files:**
- Modify: `frontend/tailwind.config.js`

- [ ] **Step 1: Update Tailwind config**

Replace the entire file content:

```js
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'nav-accent': '#90caf9',
      },
    },
  },
  plugins: [],
}
```

Note: The existing config uses `export default` (ESM). Keep that form.

---

### Task 3: Replace inline `style` props in Layout.tsx with Tailwind `className`

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Update Layout.tsx**

Replace the entire file content:

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
        </Toolbar>
      </AppBar>
      <Outlet />
    </>
  )
}

export default Layout
```

- [ ] **Step 2: Run the Layout tests to confirm they pass**

```bash
cd frontend && npx jest src/components/Layout.test.tsx --no-coverage
```

Expected: 4 PASS

- [ ] **Step 3: Run the full test suite to confirm no regressions**

```bash
cd frontend && npx jest --no-coverage
```

Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/tailwind.config.js frontend/src/components/Layout.tsx frontend/src/components/Layout.test.tsx
git commit -m "feat: replace Layout.tsx inline styles with Tailwind classes"
```
