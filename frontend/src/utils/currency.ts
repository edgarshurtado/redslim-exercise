// Currency unit is defined by spec 002 (Data.value is stored in DKK).
// If the storage currency ever changes, update this single helper.
export function formatCurrency(value: number): string {
  return value.toLocaleString('da-DK', {
    style: 'currency',
    currency: 'DKK',
    maximumFractionDigits: 0,
  })
}
