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

describe('Evolution page — options fetch', () => {
  beforeEach(() => mockedGet.mockReset())
  afterEach(() => jest.clearAllMocks())

  it('fetches brand options and enables Value select after Category is chosen', async () => {
    mockedGet.mockResolvedValue({ data: ['Brand A', 'Brand B'] })
    renderPage()

    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand' }))

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        '/market-data/evolution/options/?category=brand'
      )
    )

    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Value' })).not.toHaveAttribute('aria-disabled', 'true')
    )

    await userEvent.click(screen.getByRole('combobox', { name: 'Value' }))
    expect(await screen.findByRole('option', { name: 'Brand A' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Brand B' })).toBeInTheDocument()
  })

  it('Value select stays disabled while options are loading', async () => {
    mockedGet.mockReturnValue(new Promise(() => {}))
    renderPage()

    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Market' }))

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        '/market-data/evolution/options/?category=market'
      )
    )

    expect(screen.getByRole('combobox', { name: 'Value' })).toHaveAttribute('aria-disabled', 'true')
  })
})

describe('Evolution page — chart render', () => {
  beforeEach(() => mockedGet.mockReset())
  afterEach(() => jest.clearAllMocks())

  it('renders bar chart with year data after both selectors are set', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url.includes('options')) return Promise.resolve({ data: ['Brand A'] })
      if (url.includes('chart')) {
        return Promise.resolve({
          data: [
            { year: 2020, total: '1000.00' },
            { year: 2021, total: '2000.00' },
          ],
        })
      }
      return Promise.reject(new Error(`unexpected url: ${url}`))
    })
    renderPage()

    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand' }))
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Value' })).not.toHaveAttribute('aria-disabled', 'true')
    )
    await userEvent.click(screen.getByRole('combobox', { name: 'Value' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand A' }))

    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith(
        '/market-data/evolution/chart/?category=brand&value=Brand%20A'
      )
    )

    expect(await screen.findByTestId('bar-chart')).toBeInTheDocument()
    expect(screen.getByText('2020')).toBeInTheDocument()
    expect(screen.getByText('2021')).toBeInTheDocument()
  })

  it('shows No data available when chart endpoint returns empty array', async () => {
    mockedGet.mockImplementation((url: string) => {
      if (url.includes('options')) return Promise.resolve({ data: ['Brand A'] })
      if (url.includes('chart')) return Promise.resolve({ data: [] })
      return Promise.reject(new Error(`unexpected url: ${url}`))
    })
    renderPage()

    await userEvent.click(screen.getByRole('combobox', { name: 'Category' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand' }))
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Value' })).not.toHaveAttribute('aria-disabled', 'true')
    )
    await userEvent.click(screen.getByRole('combobox', { name: 'Value' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Brand A' }))

    await waitFor(() => expect(screen.getByText('No data available')).toBeInTheDocument())
  })
})
