# TypeScript Migration Design

**Date:** 2026-04-27  
**Scope:** Frontend only (`redslim-exercise/frontend/`)  
**Goal:** Migrate all frontend source files from JSX/JS to TypeScript with strict mode enabled.

---

## Approach

Use **babel-jest + `@babel/preset-typescript`** for Jest (type-stripping only, no type checking during test runs) combined with a separate `tsc --noEmit` script for type verification. Vite handles TypeScript natively with no additional plugins required.

This keeps test runs fast and separates type checking from test execution — the standard pattern for Vite-based React projects.

---

## File Renames

| Before | After |
|---|---|
| `src/App.jsx` | `src/App.tsx` |
| `src/App.test.jsx` | `src/App.test.tsx` |
| `src/api/client.js` | `src/api/client.ts` |
| `src/main.jsx` | `src/main.tsx` |
| `src/setupTests.js` | `src/setupTests.ts` |
| `vite.config.js` | `vite.config.ts` |

`babel.config.cjs` and `jest.config.cjs` remain `.cjs` — required by Node due to `"type": "module"` in `package.json`.

---

## New Files

### `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "lib": ["ESNext", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

### `tsconfig.node.json`

Separate config for Vite's Node context (`vite.config.ts`):

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

---

## Config Changes

### `babel.config.cjs`

Add `@babel/preset-typescript` so Babel can strip types for Jest:

```js
module.exports = {
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' } }],
    ['@babel/preset-react', { runtime: 'automatic' }],
    '@babel/preset-typescript'
  ]
}
```

### `jest.config.cjs`

Extend the transform pattern to cover `.tsx?` and update the setupTests path:

```js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  transform: {
    '^.+\\.[jt]sx?$': 'babel-jest'
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
  },
  testPathIgnorePatterns: ['/node_modules/', '/dist/']
}
```

### `package.json`

New devDependencies:
- `typescript`
- `@babel/preset-typescript`

New script:
```json
"typecheck": "tsc --noEmit"
```

---

## Type Annotations

Only 2 lines of annotation are added across the entire codebase:

**`src/main.tsx`** — non-null assertion for guaranteed DOM element:
```ts
createRoot(document.getElementById('root')!).render(...)
```

**`src/App.tsx`** — explicit type parameter for `useState` to satisfy strict null checks:
```ts
const [message, setMessage] = useState<string | null>(null)
```

All other files require rename only — no code changes.

---

## Verification

After migration, all three of the following must pass:

1. `npm test` — all Jest tests pass
2. `npm run typecheck` — `tsc --noEmit` exits with no errors
3. `npm run build` — Vite builds successfully
