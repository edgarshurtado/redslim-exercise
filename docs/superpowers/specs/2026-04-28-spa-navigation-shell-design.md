# SPA Navigation Shell Design

**Date:** 2026-04-28
**Branch:** exploration_table

## Overview

Add a top navbar and React Router-based SPA shell to the frontend. The navbar displays the app title on the left and navigation links to the right. Two routes exist: a landing page (existing content) and an Explore placeholder page.

## Architecture

React Router v6 Layout + Outlet pattern. A single `Layout` component holds the `AppBar` and renders child routes via `<Outlet />`. `App.tsx` owns the route configuration. All pages share the same navbar automatically.

### File structure changes

```
frontend/src/
  main.tsx              — wrap App in <BrowserRouter>
  App.tsx               — changed: defines route tree (no JSX content of its own)
  components/
    Layout.tsx          — new: MUI AppBar + <Outlet />
  pages/
    Landing.tsx         — new: current App content moved here
    Explore.tsx         — new: placeholder page
  api/client.ts         — unchanged
```

### Route tree

```
<BrowserRouter>
  <Routes>
    <Route element={<Layout />}>
      <Route path="/" element={<Landing />} />
      <Route path="/explore" element={<Explore />} />
    </Route>
  </Routes>
</BrowserRouter>
```

## Components

### Layout.tsx

- MUI `AppBar` with `position="static"` (scrolls with page, avoids content overlap)
- Navbar background: `#1a1a2e` (dark navy)
- Left: app title "Edgar's ReadSlim Exercise" — a `RouterLink` to `/`, white bold text
- Right of title: "Explore" link — `RouterLink` to `/explore`, `#90caf9` (MUI light blue), 16px `margin-left`
- Active route link gets `borderBottom: '2px solid #90caf9'` via `sx` prop, determined by comparing `useLocation().pathname` to the link's target path
- Below AppBar: `<Outlet />` renders the matched child route

### Landing.tsx

Current `App.tsx` content moved verbatim:
- MUI `Container` + `Box` with top margin
- `Typography h2`: "Hello Redslim"
- `Typography body1`: API message fetched from `/redslim-hello`

### Explore.tsx

Minimal placeholder:
- MUI `Container` + `Box` with top margin
- `Typography h4`: "Explore"
- No data fetching; content is added in a future spec

## Dependencies

Add `react-router-dom` to `frontend/package.json` dependencies. No other new dependencies.

## Testing

- `App.test.tsx` — updated to use `MemoryRouter`; verifies `/` renders Landing content and `/explore` renders the Explore heading
- `Landing.test.tsx` — new: moves existing App tests (Hello Redslim heading, API message) here
- No tests for `Layout.tsx` or `Explore.tsx` beyond what `App.test.tsx` covers via routing

## Out of scope

- Explore page data table (future spec: 005_exploration_table)
- Mobile responsive navbar (hamburger menu)
- MUI theme customisation beyond AppBar color
- Authentication or protected routes
