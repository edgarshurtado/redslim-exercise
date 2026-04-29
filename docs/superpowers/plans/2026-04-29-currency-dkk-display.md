# Currency Display: USD → DKK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch the Dominance treemap tooltip and the Sales Evolution chart (YAxis + Tooltip) from USD to DKK formatting, matching the currency now declared in spec 002.

**Architecture:** Currency formatting is currently inlined three times across two files using `Intl.NumberFormat` (`toLocaleString('en-US', { currency: 'USD', … })`). We extract those three call sites into a single `formatCurrency` helper that emits Danish-locale DKK output (`da-DK` + `DKK`), then replace each call site. One source of truth — future currency changes are a one-line edit.

**Tech Stack:** TypeScript, React, Vite, Jest + Testing Library.

---

## File Structure

| File | Change |
|---|---|
| `frontend/src/utils/currency.ts` | Create — exports `formatCurrency(value: number): string` |
| `frontend/src/utils/currency.test.ts` | Create — unit tests for `formatCurrency` |
| `frontend/src/pages/Dominance.tsx` | Modify — replace inline formatter at line 101 |
| `frontend/src/pages/Evolution.tsx` | Modify — replace inline formatters at lines 150-156 (YAxis tickFormatter) and 159-164 (Tooltip formatter) |

The existing page-level tests (`Dominance.test.tsx`, `Evolution.test.tsx`) mock `recharts` so the formatter output is never rendered through them — there are no test changes needed there. Coverage of the new helper lives in `currency.test.ts`.

---

### Task 1: Add `formatCurrency` helper with tests

**Files:**
- Create: `frontend/src/utils/currency.ts`
- Test: `frontend/src/utils/currency.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/utils/currency.test.ts`:

```ts
import { formatCurrency } from './currency'

describe('formatCurrency', () => {
  it('formats integers as DKK with no decimals', () => {
    // Use a regex because Intl output uses non-breaking spaces and may
    // vary slightly across ICU versions; we just assert the parts.
    const result = formatCurrency(4200000)
    expect(result).toMatch(/4\.200\.000/)
    expect(result).toMatch(/kr\.?/)
  })

  it('rounds non-integer values to the nearest whole krone', () => {
    expect(formatCurrency(1234.56)).toMatch(/1\.235/)
  })

  it('formats zero', () => {
    expect(formatCurrency(0)).toMatch(/0/)
  })
})
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `cd frontend && npx jest src/utils/currency.test.ts`
Expected: FAIL — `Cannot find module './currency'`.

- [ ] **Step 3: Implement the helper**

Create `frontend/src/utils/currency.ts`:

```ts
// Currency unit is defined by spec 002 (Data.value is stored in DKK).
// If the storage currency ever changes, update this single helper.
export function formatCurrency(value: number): string {
  return value.toLocaleString('da-DK', {
    style: 'currency',
    currency: 'DKK',
    maximumFractionDigits: 0,
  })
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `cd frontend && npx jest src/utils/currency.test.ts`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/currency.ts frontend/src/utils/currency.test.ts
git commit -m "feat(currency): add formatCurrency helper for DKK display"
```

---

### Task 2: Use `formatCurrency` in the Dominance treemap tooltip

**Files:**
- Modify: `frontend/src/pages/Dominance.tsx` (import line near top + line 101)

- [ ] **Step 1: Run the existing Dominance tests to confirm green baseline**

Run: `cd frontend && npx jest src/pages/Dominance.test.tsx`
Expected: PASS — all existing tests pass.

- [ ] **Step 2: Add the import**

Open `frontend/src/pages/Dominance.tsx`. Below the existing `import apiClient from '../api/client'` line, add:

```ts
import { formatCurrency } from '../utils/currency'
```

- [ ] **Step 3: Replace the inline formatter at line 101**

In `CustomTooltip`, replace this line:

```tsx
        {d.size.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}
```

with:

```tsx
        {formatCurrency(d.size)}
```

- [ ] **Step 4: Run the Dominance tests**

Run: `cd frontend && npx jest src/pages/Dominance.test.tsx`
Expected: PASS — same tests still pass (Tooltip is mocked, so output is unchanged from the test's perspective).

- [ ] **Step 5: Run the type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Dominance.tsx
git commit -m "refactor(dominance): use formatCurrency helper for DKK tooltip"
```

---

### Task 3: Use `formatCurrency` in the Evolution chart (YAxis + Tooltip)

**Files:**
- Modify: `frontend/src/pages/Evolution.tsx` (import line near top + lines 149-165)

- [ ] **Step 1: Run the existing Evolution tests to confirm green baseline**

Run: `cd frontend && npx jest src/pages/Evolution.test.tsx`
Expected: PASS — all existing tests pass.

- [ ] **Step 2: Add the import**

Open `frontend/src/pages/Evolution.tsx`. Below the existing `import apiClient from '../api/client'` line, add:

```ts
import { formatCurrency } from '../utils/currency'
```

- [ ] **Step 3: Replace the YAxis `tickFormatter`**

Replace this block (currently lines 149-157):

```tsx
              <YAxis
                tickFormatter={(v: number) =>
                  v.toLocaleString('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    maximumFractionDigits: 0,
                  })
                }
              />
```

with:

```tsx
              <YAxis tickFormatter={(v: number) => formatCurrency(v)} />
```

- [ ] **Step 4: Replace the `Tooltip` `formatter`**

Replace this block (currently lines 159-165):

```tsx
              <Tooltip
                formatter={(v) =>
                  typeof v === 'number'
                    ? v.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
                    : String(v ?? '')
                }
              />
```

with:

```tsx
              <Tooltip
                formatter={(v) => (typeof v === 'number' ? formatCurrency(v) : String(v ?? ''))}
              />
```

- [ ] **Step 5: Run the Evolution tests**

Run: `cd frontend && npx jest src/pages/Evolution.test.tsx`
Expected: PASS — same tests still pass (YAxis/Tooltip are mocked).

- [ ] **Step 6: Run the type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Evolution.tsx
git commit -m "refactor(evolution): use formatCurrency helper for DKK axis and tooltip"
```

---

### Task 4: Final verification (full test run + manual check)

**Files:** none modified

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd frontend && npx jest`
Expected: PASS — full suite green.

- [ ] **Step 2: Run the type check across the frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Confirm no `'USD'` references remain in `frontend/src/`**

Run: `grep -rn "USD\|en-US" frontend/src/`
Expected: no matches. (If any appear in other files outside this plan's scope, flag them — they may be unrelated, but worth noting.)

- [ ] **Step 4: Smoke-test in the browser**

Run: `cd frontend && npm run dev` (or whatever `package.json` script the project uses) and open the app.
- Visit `/dominance`, hover a brand cell — confirm the tooltip shows e.g. `4.200.000 kr.` instead of `$4,200,000`.
- Visit `/evolution`, pick a category + value — confirm both the Y-axis tick labels and the bar tooltip show DKK formatting.

If the values look wrong (currency symbol, thousand separators, decimals), investigate before claiming done.

- [ ] **Step 5: Final status check**

Run: `git status` and `git log --oneline -5`
Expected: working tree clean; three new commits on the branch from Tasks 1-3.
