# Layout.tsx — Inline Styles to Tailwind Refactor

## Goal

Replace all inline `style` props in `Layout.tsx` with Tailwind CSS classes. MUI `sx` props are out of scope and must not be changed.

## Scope

Single file: `frontend/src/components/Layout.tsx`
Config change: `frontend/tailwind.config.js`

## Changes

### 1. Tailwind config — add `nav-accent` color token

```js
theme: {
  extend: {
    colors: {
      'nav-accent': '#90caf9',
    },
  },
},
```

The `#90caf9` value (MUI blue[200]) is used in two places (link text and active border). A named token avoids duplication and makes the semantic intent clear.

### 2. Home link — replace `style` prop

Before:
```tsx
style={{
  color: '#fff',
  fontWeight: 700,
  fontSize: '16px',
  letterSpacing: '0.3px',
  textDecoration: 'none',
}}
```

After:
```tsx
className="text-white font-bold text-base tracking-[0.3px] no-underline"
```

Note: `0.3px` letter-spacing has no matching Tailwind scale step, so an arbitrary value is used.

### 3. Explore link — replace `style` prop with conditional className

Before:
```tsx
style={{
  color: '#90caf9',
  textDecoration: 'none',
  marginLeft: '16px',
  fontSize: '14px',
  ...(pathname === '/explore' && { borderBottom: '2px solid #90caf9', paddingBottom: '2px' }),
}}
```

After:
```tsx
className={`text-nav-accent no-underline ml-4 text-sm ${pathname === '/explore' ? 'border-b-2 border-nav-accent pb-0.5' : ''}`}
```

The conditional spread is replaced with a ternary inside the template literal.

## Constraints

- No new dependencies.
- No changes to `AppBar sx={{ backgroundColor: '#1a1a2e' }}` or `Toolbar sx={{ px: 4 }}`.
- Visual output must be pixel-equivalent to the current implementation.
