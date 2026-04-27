# TypeScript Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate all frontend source files from JSX/JS to TypeScript with strict mode enabled.

**Architecture:** Vite handles TypeScript natively — no plugin changes needed. Jest uses `babel-jest` + `@babel/preset-typescript` which strips types without checking them, keeping tests fast. A separate `npm run typecheck` script (`tsc --noEmit`) provides type verification. Two tsconfig files: `tsconfig.json` covers `src/` (used by Vite and the typecheck script), `tsconfig.node.json` covers `vite.config.ts` (used by editors).

**Tech Stack:** TypeScript, @babel/preset-typescript, Vite, Jest/babel-jest, React 19, MUI

---

## File Map

```
frontend/
├── tsconfig.json           ← NEW: strict TS config for src/
├── tsconfig.node.json      ← NEW: TS config for vite.config.ts (editor use)
├── babel.config.cjs        ← MODIFY: add @babel/preset-typescript preset
├── jest.config.cjs         ← MODIFY: extend transform to [jt]sx?, update setupTests path
├── package.json            ← MODIFY: add typescript + @babel/preset-typescript, add typecheck script
├── vite.config.js          ← RENAME → vite.config.ts (no code changes)
└── src/
    ├── vite-env.d.ts       ← NEW: Vite ImportMeta type declarations
    ├── App.jsx             ← RENAME → App.tsx, add useState<string | null> type param
    ├── App.test.jsx        ← RENAME → App.test.tsx, use jest.mocked() for mock methods
    ├── main.jsx            ← RENAME → main.tsx, add ! non-null assertion, fix import extension
    ├── setupTests.js       ← RENAME → setupTests.ts (no code changes)
    └── api/
        └── client.js       ← RENAME → client.ts (no code changes)
```

**Note on config files:** `babel.config.cjs` and `jest.config.cjs` stay `.cjs` — Node requires CommonJS for these because `package.json` has `"type": "module"`.

---

## Task 1: Install TypeScript packages and add typecheck script

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install TypeScript and the Babel TypeScript preset**

Run from `redslim-exercise/frontend/`:
```bash
npm install --save-dev typescript @babel/preset-typescript
```
Expected: both packages appear in `devDependencies` in `package.json`.

- [ ] **Step 2: Add the typecheck script to package.json**

In `frontend/package.json`, update the `scripts` section to:
```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "test": "jest",
  "typecheck": "tsc --noEmit"
}
```

- [ ] **Step 3: Verify tests still pass**

```bash
npm test
```
Expected: all 3 tests pass. This confirms the installs didn't break anything.

- [ ] **Step 4: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: install typescript and @babel/preset-typescript"
```

---

## Task 2: Update Babel config for TypeScript

**Files:**
- Modify: `frontend/babel.config.cjs`

- [ ] **Step 1: Add @babel/preset-typescript to babel.config.cjs**

Replace the entire contents of `frontend/babel.config.cjs`:
```js
module.exports = {
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' } }],
    ['@babel/preset-react', { runtime: 'automatic' }],
    '@babel/preset-typescript'
  ]
}
```

- [ ] **Step 2: Verify tests still pass**

Run from `redslim-exercise/frontend/`:
```bash
npm test
```
Expected: all 3 tests pass. The added preset is additive — existing `.jsx` files are unaffected.

- [ ] **Step 3: Commit**

```bash
git add babel.config.cjs
git commit -m "chore: add @babel/preset-typescript to babel config"
```

---

## Task 3: Update Jest config for TypeScript transforms

**Files:**
- Modify: `frontend/jest.config.cjs`

- [ ] **Step 1: Extend the transform pattern in jest.config.cjs**

Replace the entire contents of `frontend/jest.config.cjs`:
```js
// .cjs extension required: package.json has "type":"module", which makes Node treat
// .js files as ESM. Jest needs CommonJS config, so .cjs forces CJS resolution.
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  transform: {
    '^.+\\.[jt]sx?$': 'babel-jest'
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
  },
  testPathIgnorePatterns: ['/node_modules/', '/dist/']
}
```

The transform regex `[jt]sx?` now matches `.js`, `.jsx`, `.ts`, and `.tsx`. The `setupFilesAfterEnv` still points to `.js` — it will be updated to `.ts` in Task 5 when the file is renamed.

- [ ] **Step 2: Verify tests still pass**

```bash
npm test
```
Expected: all 3 tests pass.

- [ ] **Step 3: Commit**

```bash
git add jest.config.cjs
git commit -m "chore: extend jest transform to cover TypeScript files"
```

---

## Task 4: Add tsconfig files and Vite type declarations

**Files:**
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/src/vite-env.d.ts`

- [ ] **Step 1: Create frontend/tsconfig.json**

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

- [ ] **Step 2: Create frontend/tsconfig.node.json**

This config is picked up by editors (VS Code, etc.) for type-checking `vite.config.ts`. It is not used by `npm run typecheck`.

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

- [ ] **Step 3: Create frontend/src/vite-env.d.ts**

Vite extends `ImportMeta` with an `env` property. Without this declaration file, TypeScript doesn't know about `import.meta.env` (used in `src/api/client.ts`).

```ts
/// <reference types="vite/client" />
```

- [ ] **Step 4: Verify typecheck fails with the expected "no inputs" error**

Run from `redslim-exercise/frontend/`:
```bash
npm run typecheck
```
Expected output:
```
error TS18003: No inputs were found in config file 'tsconfig.json'. Specified 'include' paths were '["src"]' and 'exclude' paths were '[]'.
```
This is correct — no `.ts`/`.tsx` files exist in `src/` yet (only `vite-env.d.ts`, which is a declaration file). The config is wired correctly.

- [ ] **Step 5: Commit**

```bash
git add tsconfig.json tsconfig.node.json src/vite-env.d.ts
git commit -m "chore: add tsconfig and vite type declarations"
```

---

## Task 5: Rename and migrate all source files (TDD)

**Files:**
- Rename+modify: `frontend/src/main.jsx` → `frontend/src/main.tsx`
- Rename+modify: `frontend/src/App.jsx` → `frontend/src/App.tsx`
- Rename+modify: `frontend/src/App.test.jsx` → `frontend/src/App.test.tsx`
- Rename: `frontend/src/api/client.js` → `frontend/src/api/client.ts`
- Rename: `frontend/src/setupTests.js` → `frontend/src/setupTests.ts`
- Rename: `frontend/vite.config.js` → `frontend/vite.config.ts`
- Modify: `frontend/jest.config.cjs` (update setupTests path to `.ts`)

- [ ] **Step 1: Rename all files**

Run from `redslim-exercise/frontend/`:
```bash
git mv src/main.jsx src/main.tsx
git mv src/App.jsx src/App.tsx
git mv "src/App.test.jsx" "src/App.test.tsx"
git mv src/api/client.js src/api/client.ts
git mv src/setupTests.js src/setupTests.ts
git mv vite.config.js vite.config.ts
```

- [ ] **Step 2: Update jest.config.cjs to point at setupTests.ts**

Replace the entire contents of `frontend/jest.config.cjs`:
```js
// .cjs extension required: package.json has "type":"module", which makes Node treat
// .js files as ESM. Jest needs CommonJS config, so .cjs forces CJS resolution.
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

- [ ] **Step 3: Run typecheck to confirm it fails (TDD red)**

```bash
npm run typecheck
```
Expected: TypeScript errors including:
- `src/main.tsx`: `Argument of type 'HTMLElement | null' is not assignable to parameter of type 'Element | DocumentFragment'`
- `src/App.tsx`: `Argument of type 'string' is not assignable to parameter of type 'SetStateAction<null>'`
- `src/App.test.tsx`: `Property 'mockReset' does not exist on type` (mock methods not on `AxiosInstance`)

This is the expected red state — the files need annotations.

- [ ] **Step 4: Fix src/main.tsx**

Replace the entire contents of `frontend/src/main.tsx`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```
Changes: added `!` non-null assertion on `getElementById` (element is guaranteed by `index.html`), removed `.jsx` extension from the App import.

- [ ] **Step 5: Fix src/App.tsx**

Replace the entire contents of `frontend/src/App.tsx`:
```tsx
import { useState, useEffect } from 'react'
import { Typography, Container, Box } from '@mui/material'
import apiClient from './api/client'

function App() {
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

export default App
```
Change: `useState(null)` → `useState<string | null>(null)` so TypeScript knows `message` can hold a string.

- [ ] **Step 6: Fix src/App.test.tsx**

Replace the entire contents of `frontend/src/App.test.tsx`:
```tsx
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'
import apiClient from './api/client'

jest.mock('./api/client', () => ({
  __esModule: true,
  default: {
    get: jest.fn()
  }
}))

beforeEach(() => {
  jest.mocked(apiClient.get).mockReset()
})

test('renders Hello Redslim heading', () => {
  jest.mocked(apiClient.get).mockReturnValue(new Promise(() => {}))
  render(<App />)
  expect(screen.getByRole('heading', { name: /hello redslim/i })).toBeInTheDocument()
})

test('displays API response message', async () => {
  jest.mocked(apiClient.get).mockResolvedValue({ data: { message: 'Hello Redslim' } })
  render(<App />)
  await waitFor(() => {
    expect(screen.getByTestId('api-message')).toHaveTextContent('Hello Redslim')
  })
})

test('displays error message when API fails', async () => {
  jest.mocked(apiClient.get).mockRejectedValue(new Error('Network Error'))
  render(<App />)
  await waitFor(() => {
    expect(screen.getByTestId('api-message')).toHaveTextContent('Could not reach the server.')
  })
})
```
Change: `apiClient.get.mockReset()` → `jest.mocked(apiClient.get).mockReset()` (and same pattern for all mock method calls). `jest.mocked()` is the TypeScript-aware helper that tells the compiler `apiClient.get` is a `jest.MockedFunction`, giving access to `.mockReset()`, `.mockReturnValue()`, etc.

- [ ] **Step 7: Run typecheck to confirm it passes (TDD green)**

```bash
npm run typecheck
```
Expected: exits with no output and exit code 0 (no errors).

- [ ] **Step 8: Run tests to confirm they all pass**

```bash
npm test
```
Expected:
```
PASS  src/App.test.tsx
  ✓ renders Hello Redslim heading
  ✓ displays API response message
  ✓ displays error message when API fails
```

- [ ] **Step 9: Run build to confirm Vite handles TypeScript**

```bash
npm run build
```
Expected: build completes without errors, outputting files to `dist/`.

- [ ] **Step 10: Commit**

```bash
git add src/main.tsx src/App.tsx src/App.test.tsx src/api/client.ts src/setupTests.ts vite.config.ts jest.config.cjs
git commit -m "feat: migrate frontend to TypeScript with strict mode"
```
