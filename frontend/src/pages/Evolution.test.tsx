import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Evolution from './Evolution'
import apiClient from '../api/client'

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ data }: { data: Array<{ year: number }> }) => (
    <div data-testid="bar-chart">
      {data?.map((d) => (
        <div key={d.year} data-testid="bar-year">
          {d.year}
        </div>
      ))}
    </div>
  ),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

jest.mock('../api/client', () => ({
  __esModule: true,
  default: { get: jest.fn() },
}))
const mockedGet = apiClient.get as jest.Mock

function renderPage() {
  return render(
    <MemoryRouter>
      <Evolution />
    </MemoryRouter>
  )
}

describe('Evolution page — initial state', () => {
  beforeEach(() => mockedGet.mockReset())
  afterEach(() => jest.clearAllMocks())

  it('renders Category and Value selects', () => {
    renderPage()
    expect(screen.getByRole('combobox', { name: 'Category' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Value' })).toBeInTheDocument()
  })

  it('shows placeholder message before any selection', () => {
    renderPage()
    expect(
      screen.getByText('Select a category and a value to see the evolution chart.')
    ).toBeInTheDocument()
  })

  it('Value select is disabled before category is chosen', () => {
    renderPage()
    expect(screen.getByRole('combobox', { name: 'Value' })).toHaveAttribute('aria-disabled', 'true')
  })

  it('does not call the API on initial render', () => {
    renderPage()
    expect(mockedGet).not.toHaveBeenCalled()
  })
})
