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
