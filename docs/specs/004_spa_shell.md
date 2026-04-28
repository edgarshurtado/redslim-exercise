# Spec 004 - SPA Navigation Shell Design

**Date:** 2026-04-28
**Branch:** exploration_table

## Overview

Add a top navbar and React Router-based SPA shell to the frontend. The navbar displays the app title on the left and navigation links to the right. Two routes exist: a landing page (existing content) and an Explore placeholder page.

## Architecture

React Router v6 Layout + Outlet pattern. A single `Layout` component holds the `AppBar` and renders child routes via `<Outlet />`. `App.tsx` owns the route configuration. All pages share the same navbar automatically.

### File structure changes

```
frontend/
  tailwind.config.js    — extended: nav-accent color token (#90caf9)
  src/
    main.tsx            — wrap App in <BrowserRouter>
    App.tsx             — changed: defines route tree (no JSX content of its own)
    components/
      Layout.tsx        — new: MUI AppBar + <Outlet />
    pages/
      Landing.tsx       — new: current App content moved here
      Explore.tsx       — new: placeholder page
      Dominance.tsx     — new: manufacturer dominance treemap page
    api/client.ts       — unchanged
```

### Route tree

```
<BrowserRouter>
  <Routes>
    <Route element={<Layout />}>
      <Route path="/" element={<Landing />} />
      <Route path="/explore" element={<Explore />} />
      <Route path="/dominance" element={<Dominance />} />
    </Route>
  </Routes>
</BrowserRouter>
```

## Components

### Layout.tsx

- MUI `AppBar` with `position="static"` (scrolls with page, avoids content overlap)
- Navbar background: `#1a1a2e` (dark navy)
- Left: app title "Edgar's ReadSlim Exercise" — a `RouterLink` to `/` with classes `text-white font-bold text-base tracking-[0.3px] no-underline`
- Right of title: "Explore" link — a `RouterLink` to `/explore` with classes `text-nav-accent no-underline ml-4 text-sm`; `nav-accent` (`#90caf9`) is defined in `tailwind.config.js`
- Next: "Dominance" link — a `RouterLink` to `/dominance` with the same classes as "Explore"
- Active route indicator: each nav link gains `border-b-2 border-nav-accent pb-0.5` via a Tailwind `className` ternary comparing `useLocation().pathname` to its respective path
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
- `Layout.test.tsx` — 2 tests verifying the Explore link active-state indicator is applied at `/explore` and absent elsewhere
- No tests for `Explore.tsx` beyond what `App.test.tsx` covers via routing

## Out of scope

- Explore page data table (future spec: 005_exploration_table)
- Mobile responsive navbar (hamburger menu)
- MUI theme customisation beyond AppBar color
- Authentication or protected routes
